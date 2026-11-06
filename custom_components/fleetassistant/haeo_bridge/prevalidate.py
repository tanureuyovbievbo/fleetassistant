"""Referential-integrity pre-validation for a HAEO network plan.

Everything here runs BEFORE any config-flow call (ADR-0007): the site must fail
with a fleetassistant repair issue, not with a broken HAEO entry.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..profile.schema import Issue
from .plan import NetworkPlan

#: HAEO element/entity name constraints are UNVERIFIED; this is the
#: conservative subset that is safe for both HA names and entity ids.
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.\-]{0,59}$")


def prevalidate(plan: NetworkPlan) -> list[Issue]:
    """Return issues that must block an apply. Empty list == safe to apply."""
    issues: list[Issue] = []

    if not plan.hubs:
        issues.append(Issue("no_hubs", "plan.hubs", "a network plan needs at least one hub"))

    hub_names = [h.hub for h in plan.hubs]
    for name in hub_names:
        if not NAME_RE.match(name or ""):
            issues.append(Issue("invalid_hub_name", f"hub[{name}]", "hub name has characters HAEO may reject"))

    # -- element types (C-23) ----------------------------------------------
    if not plan.type_map.verified:
        missing = sorted({e.kind for e in plan.elements if e.haeo_type is None})
        if missing:
            issues.append(
                Issue(
                    "haeo_type_unverified",
                    "plan.type_map",
                    f"HAEO element type names are not verified for kinds: {', '.join(missing)} "
                    "(OQ-002, resolve in the e04 spike before applying)",
                )
            )

    # -- names and uniqueness ----------------------------------------------
    seen: dict[str, str] = {}
    for element in plan.elements:
        if not NAME_RE.match(element.name):
            issues.append(Issue("invalid_element_name", f"{element.system_id}.{element.name}", "name fails NAME_RE"))
        if element.identity in seen:
            issues.append(Issue("duplicate_element", element.identity, "duplicate element name in system"))
        seen[element.identity] = element.identity

    # -- connections --------------------------------------------------------
    names_by_system: dict[str, set[str]] = {}
    for element in plan.elements:
        names_by_system.setdefault(element.system_id, set()).add(element.name)

    connection_ids: set[str] = set()
    for connection in plan.connections:
        known = names_by_system.get(connection.system_id, set())
        if connection.source not in known:
            issues.append(
                Issue("dangling_connection", connection.identity, f"unknown source element {connection.source!r}")
            )
        if connection.target not in known:
            issues.append(
                Issue("dangling_connection", connection.identity, f"unknown target element {connection.target!r}")
            )
        if connection.source == connection.target:
            issues.append(Issue("self_connection", connection.identity, "an element cannot connect to itself"))
        if connection.identity in connection_ids:
            issues.append(Issue("duplicate_connection", connection.identity, "duplicate connection"))
        connection_ids.add(connection.identity)

    # -- horizons -----------------------------------------------------------
    for hub in plan.hubs:
        if hub.horizon_mode == "preset" and hub.preset_days is None:
            issues.append(Issue("horizon_incomplete", f"hub[{hub.hub}]", "preset horizon needs preset_days"))
        if hub.horizon_mode == "forecast_sensor" and not hub.forecast_entity:
            issues.append(
                Issue("horizon_incomplete", f"hub[{hub.hub}]", "forecast_sensor horizon needs forecast_entity")
            )

    # -- battery degradation term (C-14) ------------------------------------
    for element in plan.elements:
        if element.kind == "battery" and "degradation_cost" not in element.params:
            issues.append(
                Issue(
                    "degradation_missing",
                    f"{element.system_id}.{element.name}",
                    "battery has no degradation_cost; unpriced cycling is not allowed (C-14)",
                )
            )

    # -- one optimizer per system (C-11) ------------------------------------
    per_system = [h.system_id for h in plan.hubs]
    if len(per_system) != len(set(per_system)):
        issues.append(Issue("dual_optimizer", "plan.hubs", "a system may have exactly one hub (C-11)"))

    return issues


def blocking(issues: Iterable[Issue]) -> list[Issue]:
    return [issue for issue in issues if issue.is_error]
