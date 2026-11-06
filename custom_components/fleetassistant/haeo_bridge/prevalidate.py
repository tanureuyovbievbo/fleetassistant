"""Referential-integrity pre-validation for a HAEO network plan.

Everything here runs BEFORE any config-flow call (ADR-0007): the site must fail
with a fleetassistant repair issue, not with a broken HAEO entry.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..profile.schema import Issue
from . import contracts, fields
from .plan import CONNECTED_KINDS, NetworkPlan

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
    unknown = sorted(
        {
            str(element.haeo_type)
            for element in plan.elements
            if element.haeo_type is not None and not contracts.is_known_element_type(element.haeo_type)
        }
    )
    if unknown:
        issues.append(
            Issue(
                "haeo_type_unknown",
                "plan.type_map",
                f"not a HAEO element type at {contracts.HAEO_SURFACE_VERSION}: {', '.join(unknown)}",
            )
        )

    if not plan.type_map.verified and plan.elements:
        issues.append(
            Issue(
                "haeo_type_unverified",
                "plan.type_map",
                "element types are source-verified against "
                f"haeo@{contracts.HAEO_SURFACE_VERSION} but not confirmed on a live instance "
                "(tests/contract/haeo must pass first; OQ-002, C-23)",
            )
        )

    missing = sorted({e.kind for e in plan.elements if e.haeo_type is None})
    if missing:
        issues.append(
            Issue(
                "haeo_kind_unmapped",
                "plan.type_map",
                f"no HAEO element type recorded for kinds: {', '.join(missing)} "
                f"(HAEO {contracts.HAEO_SURFACE_VERSION} has no element of that name; record the "
                "modelling decision, OQ-002)",
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

    # -- element fields (OQ-017) -------------------------------------------
    for element in plan.elements:
        for section, name in element.missing_fields:
            issues.append(
                Issue(
                    "haeo_field_missing",
                    f"{element.system_id}.{element.name}",
                    f"HAEO field {section}.{name} is required for {element.kind!r} but the profile gives no value",
                )
            )
        if element.kind in CONNECTED_KINDS:
            if element.connection is None:
                issues.append(
                    Issue(
                        "element_unconnected",
                        f"{element.system_id}.{element.name}",
                        "HAEO requires a connection target on this element",
                    )
                )
            elif fields.is_switchboard(element.connection):
                # Resolved from the hub's own junction subentries at apply time
                # (ADR-0025); the name is a translated string we cannot know here.
                pass
            elif element.connection not in names_by_system.get(element.system_id, set()):
                issues.append(
                    Issue(
                        "dangling_connection",
                        f"{element.system_id}.{element.name}",
                        f"connection target {element.connection!r} is not an element of this system",
                    )
                )
        for key in element.ignored_keys:
            issues.append(
                Issue(
                    "profile_key_unmapped",
                    f"{element.system_id}.{element.name}",
                    f"profile key {key!r} has no HAEO field and is not written",
                    severity="warning",
                )
            )

    # -- horizons -----------------------------------------------------------
    for hub in plan.hubs:
        if hub.horizon_mode == "preset" and hub.preset_days is None:
            issues.append(Issue("horizon_incomplete", f"hub[{hub.hub}]", "preset horizon needs preset_days"))
        if hub.horizon_mode == "preset" and hub.horizon_preset is None:
            presets = ", ".join(sorted(contracts.HORIZON_PRESETS))
            issues.append(
                Issue(
                    "horizon_preset_unsupported",
                    f"hub[{hub.hub}]",
                    f"HAEO {contracts.HAEO_SURFACE_VERSION} offers only {presets}; got {hub.preset_days} days",
                )
            )
        if hub.horizon_mode == "forecast_sensor" and not hub.forecast_entity:
            issues.append(
                Issue("horizon_incomplete", f"hub[{hub.hub}]", "forecast_sensor horizon needs forecast_entity")
            )

    # -- battery degradation term (C-14) ------------------------------------
    for element in plan.elements:
        if element.kind == "battery" and not element.profile_extras.get("degradation_cost"):
            issues.append(
                Issue(
                    "degradation_missing",
                    f"{element.system_id}.{element.name}",
                    "battery has no degradation_cost; unpriced cycling is not allowed (C-14)",
                )
            )

    # -- policy elements (ADR-0017) -----------------------------------------
    for element in plan.elements:
        if element.haeo_type != contracts.POLICY_TYPE:
            continue
        rules = element.flat.get(contracts.POLICY_RULES_FIELD)
        where = f"{element.system_id}.{element.name}"
        if element.connection is not None:
            issues.append(
                Issue("policy_connected", where, "a HAEO policy element has no connection target")
            )
        if not rules:
            issues.append(
                Issue("policy_rules_missing", where, "a policy element needs at least one rule")
            )
            continue
        known = names_by_system.get(element.system_id, set())
        for index, rule in enumerate(rules):
            price = (rule.get("price") or {}).get("value")
            if price is None or float(price) < 0:
                issues.append(
                    Issue(
                        "policy_price_invalid",
                        f"{where}.rules[{index}]",
                        f"rule price must be a non-negative {contracts.POLICY_PRICE_UNIT}",
                    )
                )
            for endpoint in ("source", "target"):
                for name in rule.get(endpoint, []):
                    if name == contracts.POLICY_WILDCARD:
                        continue
                    if name not in known:
                        issues.append(
                            Issue(
                                "dangling_connection",
                                f"{where}.rules[{index}].{endpoint}",
                                f"rule names unknown element {name!r}",
                            )
                        )

    # -- one optimizer per system (C-11) ------------------------------------
    per_system = [h.system_id for h in plan.hubs]
    if len(per_system) != len(set(per_system)):
        issues.append(Issue("dual_optimizer", "plan.hubs", "a system may have exactly one hub (C-11)"))

    return issues


def blocking(issues: Iterable[Issue]) -> list[Issue]:
    return [issue for issue in issues if issue.is_error]
