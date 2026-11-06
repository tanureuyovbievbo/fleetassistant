"""Run the shared adapter contract suite against every adapter."""

from __future__ import annotations

from suite import TestAdapterContract  # noqa: F401  (pytest collects the parametrized class)

from custom_components.fleetassistant.adapters import ApiStubAdapter, ModbusStubAdapter, SafetyPipeline
from custom_components.fleetassistant.adapters.base import Command
from custom_components.fleetassistant.audit import AuditLog


def test_same_command_yields_same_decision_on_both_backings(tmp_path) -> None:
    """The safety pipeline must not special-case API vs local adapters."""
    decisions = []
    for adapter in (ApiStubAdapter(), ModbusStubAdapter()):
        audit = AuditLog(tmp_path / f"{adapter.adapter_id}.jsonl")
        pipeline = SafetyPipeline({adapter.adapter_id: adapter}, audit, consent_granted=True)
        cap = adapter.capabilities()["set_export_limit"]
        result = pipeline.submit(Command(adapter.adapter_id, cap.name, cap.max_value * 10, "contract"))
        decisions.append((result.status, result.effective_value, result.authority))

    assert decisions[0][0] == decisions[1][0] == "clamped"
    assert decisions[0][1] == 5.0
    assert decisions[1][1] == 10.0
    assert decisions[0][2] == "coarse"
    assert decisions[1][2] == "full"
