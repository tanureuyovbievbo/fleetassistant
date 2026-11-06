"""HAEO configuration surface, read from the pinned source (v0.5.0).

Everything in this module was read from ``hass-energy/haeo`` at tag ``v0.5.0``
(commit ``705bde0b1a43997dc844b60b32cbbb92032c96ea``) on 2026-11-05. It records
what HAEO *stores*, not what it *means*: names and shapes are source-verified,
while our mapping choices (which HAEO element represents our ``meter``,
``thermostat`` and ``relay`` kinds) are still open (OQ-002).

Two levels of confidence are tracked separately (ADR-0012):

* ``SOURCE_VERIFIED`` — the literal key or value in this file was read in HAEO's
  source at the pinned tag.
* ``LIVE_UNVERIFIED`` — no live HA + HAEO instance has confirmed that driving
  HAEO's config-flow API with these keys produces these records. Until the
  contract tests in ``tests/contract/haeo/`` run green, plans stay blocked
  (C-23).

Nothing here imports Home Assistant or HAEO (C-07): the bridge only ever sees
strings and dicts.

Source anchors (all ``custom_components/haeo/`` at ``v0.5.0``):

* ``const.py`` — domain, ``ELEMENT_TYPE_NETWORK``, ``CONF_INTEGRATION_TYPE``
* ``core/const.py`` — hub section keys, ``CONF_HORIZON*``, preset names
* ``core/schema/elements/element_type.py`` — :data:`ELEMENT_TYPES`
* ``core/schema/entity_value.py`` / ``constant_value.py`` — input value shapes
* ``core/schema/horizon_value.py`` + ``flows/horizon.py`` — horizon value shape
* ``flows/hub.py`` — hub creation data and per-element subentry flows
* ``core/data/forecast_times.py`` — ``forecast`` attribute boundary key
"""

from __future__ import annotations

from typing import Final

#: Pinned HAEO version this surface was read from.
HAEO_SURFACE_VERSION: Final = "0.5.0"
HAEO_SURFACE_COMMIT: Final = "705bde0b1a43997dc844b60b32cbbb92032c96ea"
HAEO_SURFACE_READ_ON_AT: Final = "2026-11-05"

#: True only after a live instance confirmed the surface end to end.
HAEO_SURFACE_LIVE_VERIFIED: Final = False

# -- identities -------------------------------------------------------------

HAEO_DOMAIN: Final = "haeo"
INTEGRATION_TYPE_HUB: Final = "hub"
ELEMENT_TYPE_NETWORK: Final = "network"

#: Every element type HAEO v0.5.0 registers (``ElementType`` members).
ELEMENT_TYPES: Final[frozenset[str]] = frozenset(
    {
        "battery",
        "battery_section",
        "buffer",
        "connection",
        "deferrable_load",
        "ev",
        "grid",
        "inverter",
        "junction",
        "load",
        "node",
        "policy",
        "solar",
    }
)

#: Element types that only appear when HAEO's advanced mode is enabled.
#: Computed by HAEO from each adapter's ``advanced`` attribute; the exact set is
#: unresolved here, so the bridge enables advanced mode rather than guessing.
ADVANCED_ONLY_TYPES_UNRESOLVED: Final = True

# -- hub records ------------------------------------------------------------

CONF_INTEGRATION_TYPE: Final = "integration_type"
CONF_NAME: Final = "name"
CONF_ELEMENT_TYPE: Final = "element_type"
CONF_HORIZON: Final = "horizon"
CONF_HORIZON_PRESET: Final = "horizon_preset"
CONF_DEBOUNCE_SECONDS: Final = "debounce_seconds"
CONF_ADVANCED_MODE: Final = "advanced_mode"
CONF_RELAX_INFEASIBLE: Final = "relax_infeasible"
CONF_RECORD_FORECASTS: Final = "record_forecasts"

HUB_SECTION_COMMON: Final = "common"
HUB_SECTION_ADVANCED: Final = "advanced"
HUB_SECTION_TIERS: Final = "tiers"

DEFAULT_DEBOUNCE_SECONDS: Final = 2

#: Horizon presets HAEO offers, mapped to the days each one covers.
HORIZON_PRESETS: Final[dict[str, int]] = {
    "2_days": 2,
    "3_days": 3,
    "5_days": 5,
    "7_days": 7,
}
DEFAULT_HORIZON_PRESET: Final = "5_days"

#: A hub's creation data is sectioned. ``relax_infeasible`` and
#: ``record_forecasts`` exist only in the hub's *options* flow, so the bridge
#: writes them after creation.
HUB_CREATE_SECTIONS: Final[tuple[str, ...]] = (HUB_SECTION_COMMON, HUB_SECTION_ADVANCED)
HUB_OPTIONS_ADVANCED_KEYS: Final[tuple[str, ...]] = (
    CONF_DEBOUNCE_SECONDS,
    CONF_ADVANCED_MODE,
    CONF_RELAX_INFEASIBLE,
    CONF_RECORD_FORECASTS,
)

#: HAEO's own default for "Relax impossible plans" is False; fleetassistant
#: defaults it to True for fleet reliability (ADR-0009), so it must be written
#: explicitly rather than inherited.
HAEO_DEFAULT_RELAX_INFEASIBLE: Final = False

# -- input value shapes -----------------------------------------------------

VALUE_TYPE_ENTITY: Final = "entity"
VALUE_TYPE_CONSTANT: Final = "constant"
CORE_INPUT_TYPES: Final[frozenset[str]] = frozenset({VALUE_TYPE_ENTITY, VALUE_TYPE_CONSTANT})

#: A horizon is a tagged value, never a bare string:
#: preset -> ``{"value": "5_days"}``, forecast sensor -> ``{"value": ["sensor.id"]}``.
HORIZON_VALUE_KEY: Final = "value"
HORIZON_ENTITY_KEY: Final = "value"

#: Time-series points inside a ``forecast`` attribute name their boundary
#: ``time`` (ISO 8601). ``n + 1`` points describe ``n`` periods.
FORECAST_ATTRIBUTE: Final = "forecast"
FORECAST_BOUNDARY_KEY: Final = "time"
FORECAST_VALUE_KEY: Final = "value"
FORECAST_MIN_BOUNDARIES: Final = 2

# -- kind mapping (our kinds -> HAEO element types) -------------------------

#: HAEO element type per profile element kind, where the correspondence is
#: unambiguous from HAEO's own element list.
#:
#: ``ev_charger`` maps to ``deferrable_load``: HAEO's ``ev`` models a *vehicle*
#: (capacity, energy per distance, current SOC, connected flag) which a charger
#: profile does not have, while a deferrable load asks only for a run-window
#: calendar and a power cap (ADR-0016).
#:
#: ``meter``, ``thermostat`` and ``relay`` map to ``None`` on purpose: HAEO has
#: no element with that name, and choosing a substitute is a modelling decision,
#: not a naming lookup. Those kinds block an apply until the decision is
#: recorded (OQ-002, OQ-021).
CANDIDATE_KIND_TO_TYPE: Final[dict[str, str | None]] = {
    "grid": "grid",
    "solar": "solar",
    "battery": "battery",
    "load": "load",
    "ev_charger": "deferrable_load",
    "meter": None,
    "thermostat": None,
    "relay": None,
}

#: Kinds with no HAEO element type yet; each needs a recorded decision.
UNRESOLVED_KINDS: Final[frozenset[str]] = frozenset(
    kind for kind, haeo_type in CANDIDATE_KIND_TO_TYPE.items() if haeo_type is None
)

#: Profile fields that HAEO stores as element inputs. ``fields.py`` records the
#: section and field name of each; the mapping is source-verified and
#: live-unverified (OQ-017).
INPUT_FIELD_NAMES_UNRESOLVED: Final = False

#: Subentry type HAEO's hub flow creates on its own (``flows/hub.py``). It holds
#: the network, not a power element, so it is never part of a network plan.
NON_ELEMENT_SUBENTRY_TYPES: Final[frozenset[str]] = frozenset({"network"})

#: HAEO has no connection record: ``ConnectedCommonConfig`` requires a
#: ``connection`` field on each element, holding
#: ``{"type": "connection_target", "value": "<junction name>"}``
#: (``core/schema/sections/common.py``). Topology is therefore expressed by
#: pointing elements at a junction, which is HAEO's own switchboard (ADR-0025).
CONNECTIONS_ARE_ELEMENT_FIELDS: Final = True

#: Whether an apply may delete elements it did not create. HAEO's hub flow
#: creates a switchboard junction of its own, and we do not yet track which
#: subentries we own, so pruning stays off and an unexpected element is reported
#: instead of deleted (OQ-018).
PRUNE_UNKNOWN_ELEMENTS: Final = False


def is_known_element_type(haeo_type: str | None) -> bool:
    """Return True when ``haeo_type`` is a type HAEO v0.5.0 registers."""
    return haeo_type in ELEMENT_TYPES


def horizon_preset_for(days: int | None) -> str | None:
    """Return the HAEO preset name covering ``days``, or None if there is none."""
    for preset, preset_days in HORIZON_PRESETS.items():
        if preset_days == days:
            return preset
    return None


def preset_days(preset: str | None) -> int | None:
    """Return the day count of a HAEO preset name, or None if unknown."""
    if preset is None:
        return None
    return HORIZON_PRESETS.get(preset)


def horizon_value(mode: str, preset: str | None = None, entity: str | None = None) -> dict[str, object]:
    """Return a horizon as HAEO stores it (tagged, not a bare string)."""
    if mode == "forecast_sensor":
        if not entity:
            raise ValueError("forecast_sensor horizon needs an entity")
        return {HORIZON_ENTITY_KEY: [entity]}
    if not preset:
        raise ValueError("preset horizon needs a preset name")
    return {HORIZON_VALUE_KEY: preset}


__all__ = [
    "ADVANCED_ONLY_TYPES_UNRESOLVED",
    "CANDIDATE_KIND_TO_TYPE",
    "CONF_ADVANCED_MODE",
    "CONF_DEBOUNCE_SECONDS",
    "CONF_ELEMENT_TYPE",
    "CONF_HORIZON",
    "CONF_HORIZON_PRESET",
    "CONF_INTEGRATION_TYPE",
    "CONF_NAME",
    "CONF_RECORD_FORECASTS",
    "CONF_RELAX_INFEASIBLE",
    "CONNECTIONS_ARE_ELEMENT_FIELDS",
    "PRUNE_UNKNOWN_ELEMENTS",
    "CORE_INPUT_TYPES",
    "DEFAULT_DEBOUNCE_SECONDS",
    "DEFAULT_HORIZON_PRESET",
    "ELEMENT_TYPES",
    "ELEMENT_TYPE_NETWORK",
    "FORECAST_ATTRIBUTE",
    "FORECAST_BOUNDARY_KEY",
    "FORECAST_MIN_BOUNDARIES",
    "FORECAST_VALUE_KEY",
    "HAEO_DEFAULT_RELAX_INFEASIBLE",
    "HAEO_DOMAIN",
    "HAEO_SURFACE_COMMIT",
    "HAEO_SURFACE_LIVE_VERIFIED",
    "HAEO_SURFACE_READ_ON_AT",
    "HAEO_SURFACE_VERSION",
    "HORIZON_ENTITY_KEY",
    "HORIZON_PRESETS",
    "HORIZON_VALUE_KEY",
    "HUB_CREATE_SECTIONS",
    "HUB_OPTIONS_ADVANCED_KEYS",
    "HUB_SECTION_ADVANCED",
    "HUB_SECTION_COMMON",
    "HUB_SECTION_TIERS",
    "INPUT_FIELD_NAMES_UNRESOLVED",
    "INTEGRATION_TYPE_HUB",
    "NON_ELEMENT_SUBENTRY_TYPES",
    "POLICY_PRICE_UNIT",
    "POLICY_RULES_FIELD",
    "POLICY_TYPE",
    "POLICY_WILDCARD",
    "UNRESOLVED_KINDS",
    "VALUE_TYPE_CONSTANT",
    "VALUE_TYPE_ENTITY",
    "horizon_preset_for",
    "horizon_value",
    "is_known_element_type",
    "preset_days",
]

# --- policy elements (``core/schema/elements/policy.py``, ``core/adapters/policy_compilation.py``)

#: Element type whose rules compile into ``PolicyPricing`` model elements.
POLICY_TYPE = "policy"
#: Policy payload key holding the rule list (plain list, not a section).
POLICY_RULES_FIELD = "rules"
#: A rule names elements, or this wildcard for "every capable element".
POLICY_WILDCARD = "*"
#: Rule price unit: currency per kWh of flow crossing the rule's cut.
POLICY_PRICE_UNIT = "currency/kWh"
