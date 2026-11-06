"""HAEO bridge package — the ONLY module that knows HAEO (C-07).

Modules:
    contracts    recorded HAEO v0.5.0 surface (names, keys, presets) + status
    plan         profile -> HAEO network plan (intermediate representation)
    prevalidate  referential integrity before any apply (ADR-0007)
    apply        idempotent diff + driver contract; nothing writes HAEO storage
    flows        flow-driven driver: answers HAEO's config/options/subentry flows
    ha_port      Home Assistant implementation of the flow port (HA import)

``ha_port`` is intentionally not re-exported here: importing it pulls in Home
Assistant, and the rest of the bridge must stay testable without it.
"""

from .apply import ApplyReport, DriverError, HaeoDriver, InMemoryHaeoDriver, Operation, apply_plan, check_version
from .flows import BridgeUnverified, EntryRecord, FlowError, FlowHaeoDriver, FlowPort, FlowStep, SubentryRecord
from .plan import ConnectionPlan, ElementPlan, HaeoTypeMap, HubPlan, NetworkPlan, compile_plan
from .prevalidate import prevalidate

__all__ = [
    "ApplyReport",
    "BridgeUnverified",
    "ConnectionPlan",
    "DriverError",
    "ElementPlan",
    "EntryRecord",
    "FlowError",
    "FlowHaeoDriver",
    "FlowPort",
    "FlowStep",
    "HaeoDriver",
    "HaeoTypeMap",
    "HubPlan",
    "InMemoryHaeoDriver",
    "NetworkPlan",
    "Operation",
    "SubentryRecord",
    "apply_plan",
    "check_version",
    "compile_plan",
    "prevalidate",
]
