"""HAEO bridge package — the ONLY module that knows HAEO (C-07).

Modules:
    plan         profile -> HAEO network plan (intermediate representation)
    prevalidate  referential integrity before any apply (ADR-0007)
    apply        idempotent diff + driver contract; nothing writes HAEO storage
"""

from .apply import ApplyReport, HaeoDriver, InMemoryHaeoDriver, Operation, apply_plan, check_version
from .plan import ConnectionPlan, ElementPlan, HaeoTypeMap, HubPlan, NetworkPlan, compile_plan
from .prevalidate import prevalidate

__all__ = [
    "ApplyReport",
    "ConnectionPlan",
    "ElementPlan",
    "HaeoDriver",
    "HaeoTypeMap",
    "HubPlan",
    "InMemoryHaeoDriver",
    "NetworkPlan",
    "Operation",
    "apply_plan",
    "check_version",
    "compile_plan",
    "prevalidate",
]
