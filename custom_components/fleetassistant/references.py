"""The entities a profile promises, and whether they exist (step 2 of the roadmap).

A profile names sensors and calendars by entity id. Home Assistant accepts any
string there: the config entry loads, HAEO builds a plan against ``unknown``, and
the failure surfaces days later as a flat battery or a price of zero. This module
collects every entity a profile depends on and checks each one against a snapshot,
so the first thing a user sees is a repair naming the entity that is missing —
not a quietly wrong plan.

Pure code: no Home Assistant import, no I/O. ``runtime.py`` builds the snapshots
and raises the repairs; the rules here are testable on a laptop.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from .profile.schema import Issue

Requirement = Literal["forecast", "calendar", "entity"]

#: Keys whose value is a single entity id, and what the consumer needs from it.
#: Prices are forecasts too: HAEO reads a price series, not a scalar.
REFERENCE_KEYS: dict[str, Requirement] = {
    "entity_id": "entity",
    "forecast_entity": "forecast",
    "import_price_entity": "forecast",
    "export_price_entity": "forecast",
    "connected_entity": "entity",
    "current_soc_entity": "entity",
    "window_calendar": "calendar",
}

PRICE_REFERENCE_KEYS = frozenset({"import_price_entity", "export_price_entity"})

#: HA's states that mean "the entity exists but cannot be read right now".
UNREADABLE_STATES = frozenset({"unavailable", "unknown"})


@dataclass(frozen=True)
class Reference:
    """One entity a profile depends on."""

    entity_id: str
    requirement: Requirement
    path: str
    label: str

    @property
    def is_calendar(self) -> bool:
        return self.requirement == "calendar"


@dataclass(frozen=True)
class EntitySnapshot:
    """What Home Assistant knows about an entity at setup time."""

    state: str
    forecast_points: int = 0
    unit: str | None = None

    @property
    def readable(self) -> bool:
        return self.state not in UNREADABLE_STATES


def collect_references(
    profile: Mapping[str, Any],
    *,
    published: Iterable[str] = (),
) -> tuple[Reference, ...]:
    """Return every entity reference in a profile, in a stable order.

    ``published`` lists entity ids this integration creates itself (the price
    sensors): they are references like any other, but a missing one is our bug,
    not the user's, so callers usually exclude them.
    """
    skip = {entity_id for entity_id in published}
    found: dict[tuple[str, str], Reference] = {}

    def add(entity_id: Any, requirement: Requirement, path: str, label: str) -> None:
        if not isinstance(entity_id, str) or not entity_id:
            return
        if entity_id in skip:
            return
        found.setdefault((entity_id, requirement), Reference(entity_id, requirement, path, label))

    for index, system in enumerate(_sequence(profile.get("systems"))):
        for e_index, element in enumerate(_sequence(_mapping(system).get("elements"))):
            if not isinstance(element, Mapping):
                continue
            element_id = str(element.get("id") or f"element[{e_index}]")
            for key, requirement in REFERENCE_KEYS.items():
                if key in element:
                    add(element.get(key), requirement, f"$.systems[{index}].elements[{e_index}].{key}", element_id)

    for index, control in enumerate(_sequence(profile.get("controls"))):
        if not isinstance(control, Mapping):
            continue
        if "entity_id" in control:
            add(
                control.get("entity_id"),
                "entity",
                f"$.controls[{index}].entity_id",
                str(control.get("id") or f"control[{index}]"),
            )

    horizon = _mapping(_mapping(_mapping(profile.get("site")).get("haeo")).get("horizon"))
    if "forecast_entity" in horizon:
        add(horizon.get("forecast_entity"), "forecast", "$.site.haeo.horizon.forecast_entity", "horizon")

    return tuple(found.values())


def check_references(
    references: Iterable[Reference],
    lookup: Callable[[str], EntitySnapshot | None],
    *,
    min_forecast_points: int = 2,
) -> list[Issue]:
    """Compare references against snapshots and return one issue per problem.

    Codes: ``entity_missing`` (nothing by that id), ``entity_unavailable`` (exists
    but unreadable), ``entity_no_forecast`` (fewer than ``min_forecast_points``
    points, so HAEO cannot build a horizon), ``calendar_domain_mismatch``.
    """
    issues: list[Issue] = []
    for reference in references:
        snapshot = lookup(reference.entity_id)
        if snapshot is None:
            issues.append(
                Issue(
                    "entity_missing",
                    reference.path,
                    f"{reference.label} references {reference.entity_id}, which does not exist",
                )
            )
            continue
        if not snapshot.readable:
            issues.append(
                Issue(
                    "entity_unavailable",
                    reference.path,
                    f"{reference.label} references {reference.entity_id}, which is {snapshot.state}",
                    severity="warning",
                )
            )
            continue
        if reference.is_calendar:
            if not reference.entity_id.startswith("calendar."):
                issues.append(
                    Issue(
                        "calendar_domain_mismatch",
                        reference.path,
                        f"{reference.label} needs a calendar entity, got {reference.entity_id}",
                    )
                )
            continue
        if reference.requirement == "forecast" and snapshot.forecast_points < min_forecast_points:
            issues.append(
                Issue(
                    "entity_no_forecast",
                    reference.path,
                    f"{reference.label} references {reference.entity_id}, which publishes "
                    f"{snapshot.forecast_points} forecast points (need {min_forecast_points})",
                )
            )
    return issues


def repair_key(reference: Reference) -> str:
    """A stable, one-per-reference repair identifier."""
    return f"reference_{reference.entity_id.replace('.', '_')}"


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []
