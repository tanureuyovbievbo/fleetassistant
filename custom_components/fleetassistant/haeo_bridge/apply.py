"""Apply a network plan to HAEO through a driver (idempotent diff).

The driver is the ONLY seam that talks to HAEO (C-07). Two implementations:

* ``InMemoryHaeoDriver`` — used by contract/unit tests.
* ``HomeAssistantHaeoDriver`` (runtime.py) — drives HAEO's config-flow API.

Nothing here writes HAEO storage or files (C-06): the driver only calls the
config-flow API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from ..const import SUPPORTED_HAEO_VERSIONS
from ..profile.schema import Issue
from .plan import ElementPlan, NetworkPlan
from .prevalidate import prevalidate

OperationType = Literal["create_hub", "update_hub", "remove_hub", "create_element", "update_element", "remove_element", "create_connection", "remove_connection"]
Status = Literal["applied", "noop", "blocked", "partial"]


class DriverError(RuntimeError):
    """A driver refused or could not complete a write.

    Carries a stable ``code`` (turned into a repair issue) and the ``path`` of
    the thing that failed, so a partial apply is reported item by item instead
    of vanishing into a traceback.
    """

    def __init__(self, message: str, *, code: str = "haeo_write_failed", path: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.path = path


@dataclass(frozen=True)
class Operation:
    type: OperationType
    system_id: str
    name: str
    detail: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:  # pragma: no cover - convenience
        return f"{self.type} {self.system_id}/{self.name}"


@dataclass
class ApplyReport:
    status: Status
    haeo_version: str | None = None
    operations: list[Operation] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status in ("applied", "noop")

    @property
    def applied(self) -> list[Operation]:
        return [op for op in self.operations if op.type not in ("remove_hub", "remove_element", "remove_connection")]


class HaeoDriver(Protocol):
    """Minimal contract the bridge needs from HAEO.

    Deliberately narrow: everything is expressed as hub/element/connection
    records keyed by *name* so the diff is name-stable across re-applies.
    """

    def haeo_version(self) -> str: ...

    def list_hubs(self) -> dict[str, dict[str, Any]]: ...

    def create_hub(self, name: str, options: dict[str, Any]) -> None: ...

    def update_hub(self, name: str, options: dict[str, Any]) -> None: ...

    def remove_hub(self, name: str) -> None: ...

    def list_elements(self, hub: str) -> dict[str, dict[str, Any]]: ...

    def create_element(self, hub: str, element: ElementPlan) -> None: ...

    def update_element(self, hub: str, name: str, element: ElementPlan) -> None: ...

    def remove_element(self, hub: str, name: str) -> None: ...

    def list_connections(self, hub: str) -> set[tuple[str, str]]: ...

    def create_connection(self, hub: str, source: str, target: str) -> None: ...

    def remove_connection(self, hub: str, source: str, target: str) -> None: ...


def check_version(detected: str | None, supported: tuple[str, ...] = SUPPORTED_HAEO_VERSIONS) -> Issue | None:
    """Return a blocking issue when HAEO is not a version we contract-test (ADR-0004)."""
    if detected is None:
        return Issue("haeo_missing", "haeo", "HAEO was not detected; install and configure HAEO first")
    if detected not in supported:
        return Issue(
            "haeo_version_unsupported",
            f"haeo[{detected}]",
            f"HAEO {detected} is not contract-tested by this build (supported: {', '.join(supported)})",
        )
    return None


def _element_payload(element: ElementPlan) -> dict[str, Any]:
    """What HAEO stores for an element, and therefore what the diff compares.

    ``kind`` is a profile concept and is not part of it; it only picks the type
    and decides which fields the parameters carry.
    """
    return {"type": element.haeo_type, "data": {**element.params, **element.inputs}}


def apply_plan(
    driver: HaeoDriver,
    plan: NetworkPlan,
    *,
    supported: tuple[str, ...] = SUPPORTED_HAEO_VERSIONS,
    dry_run: bool = False,
) -> ApplyReport:
    """Diff ``plan`` against live HAEO and apply the difference.

    Idempotent: re-applying an unchanged plan produces zero operations.
    Blocked on version mismatch or any pre-validation error, and nothing is
    applied in that case.
    """
    detected = driver.haeo_version()
    version_issue = check_version(detected, supported)
    if version_issue is not None:
        return ApplyReport(status="blocked", haeo_version=detected, issues=[version_issue])

    issues = prevalidate(plan)
    preflight = getattr(driver, "preflight", None)
    if preflight is not None:
        issues = issues + list(preflight(plan))
    if any(issue.is_error for issue in issues):
        return ApplyReport(status="blocked", haeo_version=detected, issues=issues)

    report = ApplyReport(status="noop", haeo_version=detected, issues=issues)
    live_hubs = driver.list_hubs()

    desired_hubs = {h.hub: h for h in plan.hubs}
    for name, hub in desired_hubs.items():
        options = hub.options()
        if name not in live_hubs:
            if not _run(report, Operation("create_hub", hub.system_id, name), driver.create_hub, dry_run, name, options):
                return report
        elif live_hubs[name].get("options") != options and not _run(
            report, Operation("update_hub", hub.system_id, name), driver.update_hub, dry_run, name, options
        ):
            return report
    for name in sorted(set(live_hubs) - set(desired_hubs)):
        if not _run(report, Operation("remove_hub", "", name), driver.remove_hub, dry_run, name):
            return report

    for hub in plan.hubs:
        live_elements = driver.list_elements(hub.hub)
        desired = [e for e in plan.elements if e.system_id == hub.system_id]
        desired_names = {e.name for e in desired}
        for element in desired:
            payload = _element_payload(element)
            if element.name not in live_elements:
                if not _run(
                    report,
                    Operation("create_element", element.system_id, element.name),
                    driver.create_element,
                    dry_run,
                    hub.hub,
                    element,
                ):
                    return report
            elif live_elements[element.name].get("payload") != payload and not _run(
                report,
                Operation("update_element", element.system_id, element.name),
                driver.update_element,
                dry_run,
                hub.hub,
                element.name,
                element,
            ):
                return report
        for name in sorted(set(live_elements) - desired_names):
            if not _run(
                report, Operation("remove_element", hub.system_id, name), driver.remove_element, dry_run, hub.hub, name
            ):
                return report

        desired_connections = {(c.source, c.target): c for c in plan.connections if c.system_id == hub.system_id}
        if not desired_connections:
            # Nothing to create; listing live links is only needed to prune them,
            # and the flow driver cannot read them yet (OQ-017).
            continue
        live_connections = driver.list_connections(hub.hub)
        for source, target in sorted(set(desired_connections) - live_connections):
            operation = Operation("create_connection", hub.system_id, f"{source}->{target}")
            if not _run(report, operation, driver.create_connection, dry_run, hub.hub, source, target):
                return report
        for source, target in sorted(live_connections - set(desired_connections)):
            operation = Operation("remove_connection", hub.system_id, f"{source}->{target}")
            if not _run(report, operation, driver.remove_connection, dry_run, hub.hub, source, target):
                return report

    if report.operations and report.status == "noop":
        report.status = "applied"
    return report


def _run(report: ApplyReport, operation: Operation, method: Any, dry_run: bool, *args: Any) -> bool:
    """Record an operation and run it; False means the apply must stop.

    The method and its arguments are passed explicitly (no closures) so a dry
    run and a real run share one code path. A failed write leaves the report
    ``partial`` with a repair-ready issue: we never claim ``applied`` for work
    that did not land (C-12, ADR-0012).
    """
    report.operations.append(operation)
    if dry_run:
        return True
    try:
        method(*args)
    except DriverError as err:
        report.issues.append(Issue(err.code, err.path or operation.name, str(err)))
        report.status = "partial"
        report.error = str(err)
        return False
    return True


class InMemoryHaeoDriver:
    """Test double implementing the driver contract. Not used in production."""

    def __init__(self, version: str = "0.5.0") -> None:
        self._version = version
        self.hubs: dict[str, dict[str, Any]] = {}
        self.elements: dict[str, dict[str, dict[str, Any]]] = {}
        self.connections: dict[str, set[tuple[str, str]]] = {}
        self.calls: list[str] = []

    # -- protocol -----------------------------------------------------------
    def haeo_version(self) -> str:
        return self._version

    def list_hubs(self) -> dict[str, dict[str, Any]]:
        return {name: dict(record) for name, record in self.hubs.items()}

    def create_hub(self, name: str, options: dict[str, Any]) -> None:
        self.calls.append(f"create_hub:{name}")
        self.hubs[name] = {"options": options}
        self.elements.setdefault(name, {})
        self.connections.setdefault(name, set())

    def update_hub(self, name: str, options: dict[str, Any]) -> None:
        self.calls.append(f"update_hub:{name}")
        self.hubs[name] = {"options": options}

    def remove_hub(self, name: str) -> None:
        self.calls.append(f"remove_hub:{name}")
        self.hubs.pop(name, None)
        self.elements.pop(name, None)
        self.connections.pop(name, None)

    def list_elements(self, hub: str) -> dict[str, dict[str, Any]]:
        return {name: dict(record) for name, record in self.elements.get(hub, {}).items()}

    def create_element(self, hub: str, element: ElementPlan) -> None:
        self.calls.append(f"create_element:{hub}/{element.name}")
        self.elements.setdefault(hub, {})[element.name] = {"payload": _element_payload(element)}

    def update_element(self, hub: str, name: str, element: ElementPlan) -> None:
        self.calls.append(f"update_element:{hub}/{name}")
        self.elements.setdefault(hub, {})[name] = {"payload": _element_payload(element)}

    def remove_element(self, hub: str, name: str) -> None:
        self.calls.append(f"remove_element:{hub}/{name}")
        self.elements.get(hub, {}).pop(name, None)

    def list_connections(self, hub: str) -> set[tuple[str, str]]:
        return set(self.connections.get(hub, set()))

    def create_connection(self, hub: str, source: str, target: str) -> None:
        self.calls.append(f"create_connection:{hub}/{source}->{target}")
        self.connections.setdefault(hub, set()).add((source, target))

    def remove_connection(self, hub: str, source: str, target: str) -> None:
        self.calls.append(f"remove_connection:{hub}/{source}->{target}")
        self.connections.setdefault(hub, set()).discard((source, target))
