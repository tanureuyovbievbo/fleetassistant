"""Device packs: data-only brand contracts (ADR-0022, OQ-023)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from helpers import repo_root

from custom_components.fleetassistant.device_packs import (
    BINDABLE_CAPABILITIES,
    DevicePack,
    controls_from_pack,
    load_pack,
    load_packs,
    pack_from_dict,
    validate_pack,
)

PACK_PATH = repo_root() / "device_packs" / "examples" / "solark_example" / "pack.json"


def _document(**overrides) -> dict:
    document = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    document.update(overrides)
    return document


def _codes(issues) -> list[str]:
    return [issue.code for issue in issues]


def test_the_example_pack_loads_and_warns_that_it_is_unverified():
    result = load_pack(PACK_PATH)

    assert result.ok
    assert isinstance(result.pack, DevicePack)
    assert result.pack.verified is False
    assert "pack_unverified" in _codes(result.issues)
    assert "source_unverified" in _codes(result.issues)


def test_the_example_pack_never_claims_a_fetched_source():
    pack = load_pack(PACK_PATH).pack
    assert pack is not None
    assert all(not source.get("url") for source in pack.sources)


def test_bindings_render_control_blocks_the_profile_schema_accepts():
    pack = load_pack(PACK_PATH).pack
    assert pack is not None

    controls = controls_from_pack(pack, element_id="grid", capabilities=("set_export_limit",))

    assert controls[0]["element"] == "grid"
    assert controls[0]["capability"] == "set_export_limit"
    assert controls[0]["entity_id"].startswith("number.")
    assert controls[0]["fail_safe_value"] == pytest.approx(12.0)


def test_a_pack_with_no_sources_is_an_error():
    document = _document()
    document["sources"] = []
    assert "pack_unsourced" in _codes(validate_pack(document))


def test_a_cloud_integration_cannot_bind_full_authority():
    document = _document()
    document["integration"] = {"domain": "tesla_fleet", "iot_class": "cloud_polling"}
    issues = validate_pack(document)
    assert "authority_cloud" in _codes(issues)
    assert any(issue.is_error for issue in issues)


def test_a_cloud_integration_may_bind_coarse_authority():
    document = _document()
    document["integration"] = {"domain": "tesla_fleet", "iot_class": "cloud_polling"}
    document["bindings"] = {
        "set_export_limit": {**document["bindings"]["set_export_limit"], "authority": "coarse", "backing": "api"}
    }
    assert not [issue for issue in validate_pack(document) if issue.is_error]


def test_an_unknown_capability_is_rejected():
    document = _document()
    document["bindings"]["set_fusion_rate"] = document["bindings"]["set_export_limit"]
    assert "capability_unknown" in _codes(validate_pack(document))


def test_a_unit_that_does_not_match_the_capability_is_rejected():
    document = _document()
    document["bindings"]["set_battery_target"]["unit"] = "kWh"
    issues = validate_pack(document)
    assert "unit" in _codes(issues)
    assert any("set_battery_target" in issue.path for issue in issues)


def test_a_fail_safe_outside_the_envelope_is_rejected():
    document = _document()
    document["bindings"]["set_export_limit"]["fail_safe_value"] = 40.0
    assert "range" in _codes(validate_pack(document))


def test_a_min_above_max_is_rejected():
    document = _document()
    document["bindings"]["set_charger_amps"] = {
        **document["bindings"]["set_battery_target"],
        "capability": "set_charger_amps",
        "unit": "A",
        "min": 48.0,
        "max": 6.0,
        "fail_safe_value": 16.0,
    }
    assert "range" in _codes(validate_pack(document))


def test_a_missing_required_binding_key_is_reported_per_key():
    document = _document()
    del document["bindings"]["set_export_limit"]["hysteresis"]
    issues = validate_pack(document)
    required = [issue for issue in issues if issue.code == "required"]
    assert len(required) == 1
    assert "hysteresis" in required[0].path


def test_an_unsupported_pack_version_is_rejected():
    assert "pack_version" in _codes(validate_pack(_document(pack_version=99)))


def test_an_unknown_iot_class_is_rejected():
    document = _document()
    document["integration"]["iot_class"] = "magic"
    assert "choice" in _codes(validate_pack(document))


def test_a_pack_with_errors_does_not_load():
    document = _document()
    document["bindings"] = {}
    path = Path("pack.json")
    result = load_pack(PACK_PATH)
    assert result.ok
    issues = validate_pack(document)
    assert any(issue.is_error for issue in issues)
    assert path  # the document alone is enough to fail; no file is written


def test_a_missing_file_is_an_issue_not_a_crash():
    result = load_pack(Path("does-not-exist") / "pack.json")
    assert result.pack is None
    assert _codes(result.issues) == ["missing_file"]


def test_invalid_json_is_an_issue_not_a_crash(tmp_path):
    bad = tmp_path / "pack.json"
    bad.write_text("{not json", encoding="utf-8")
    result = load_pack(bad)
    assert result.pack is None
    assert _codes(result.issues) == ["invalid_json"]


def test_load_packs_skips_the_nested_examples_directory():
    packs, issues = load_packs(repo_root() / "device_packs")
    # examples/<brand>/pack.json is two levels deep and must not be treated as shipped.
    assert packs == {}
    assert issues == []


def test_load_packs_reports_a_missing_root(tmp_path):
    packs, issues = load_packs(tmp_path / "nope")
    assert packs == {}
    assert _codes(issues) == ["missing_dir"]


def test_every_bindable_capability_is_one_the_adapter_layer_can_write():
    from custom_components.fleetassistant.adapters.ha_services import BINDING_BY_CAPABILITY

    assert frozenset(BINDING_BY_CAPABILITY) == BINDABLE_CAPABILITIES


def test_pack_from_dict_round_trips_the_example():
    pack = pack_from_dict(_document())
    assert pack.brand_id == "solark_example"
    assert pack.capabilities() == ("set_battery_target", "set_export_limit", "shed_circuit")
    assert pack.is_cloud is False
