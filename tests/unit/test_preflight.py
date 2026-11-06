"""Offline preflight: the report an operator gets before pointing at a site."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from helpers import EXAMPLES, REPO_ROOT

from tools.preflight import main, run_preflight

NOW = datetime(2026, 11, 6, 18, 0, tzinfo=UTC)


def test_a_gateway_profile_compiles_and_reports_its_references():
    report = run_preflight(EXAMPLES / "solark_gateway_primary.yaml", now=NOW)

    assert report.hubs == 1
    assert report.controls == 4
    assert "sensor.house_load_forecast" in report.references
    assert "number.solark_export_limit_kw" in report.references


def test_an_applyable_profile_is_still_blocked_by_the_unverified_element_map():
    report = run_preflight(EXAMPLES / "solark_gateway_primary.yaml", now=NOW)

    codes = {issue.code for issue in report.errors}
    assert "haeo_type_unverified" in codes
    assert report.ok is False


def test_unmapped_kinds_are_named_not_silently_dropped():
    report = run_preflight(EXAMPLES / "solark_gateway_primary.yaml", now=NOW)

    unmapped = [issue for issue in report.errors if issue.code == "haeo_kind_unmapped"]
    assert unmapped
    assert "thermostat" in unmapped[0].message


def test_a_broken_profile_reports_profile_errors_and_no_plan():
    report = run_preflight(EXAMPLES / "invalid" / "dangling_reference.json", now=NOW)

    assert report.ok is False
    assert report.hubs == 0
    assert report.errors


def test_tariffs_resolve_for_the_example_profile():
    report = run_preflight(EXAMPLES / "solark_gateway_primary.yaml", now=NOW)

    assert set(report.tariffs) == {"price_import", "price_export"}
    assert report.tariffs["price_import"]["points"] == 49
    assert report.tariffs["price_import"]["authority"] == "user"


def test_device_packs_are_included_when_asked(tmp_path):
    report = run_preflight(
        EXAMPLES / "solark_gateway_primary.yaml", packs_root=REPO_ROOT / "device_packs", now=NOW
    )
    # The examples directory is intentionally not a shipped pack set.
    assert not [issue for issue in report.warnings if issue.code == "pack_available"]


def test_the_cli_exits_non_zero_and_prints_a_json_report(capsys):
    exit_code = main([str(EXAMPLES / "solark_gateway_primary.yaml"), "--json"])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["site_id"] == "solark_adu_demo"
    assert payload["errors"][0]["code"]


def test_the_cli_prints_a_human_report(capsys):
    main([str(EXAMPLES / "tesla_cloud_primary.yaml")])

    out = capsys.readouterr().out
    assert "result" in out and "BLOCKED" in out
    assert "price price_import" in out


@pytest.mark.parametrize("name", ["tesla_cloud_primary.yaml", "solark_gateway_primary.yaml", "multi_hub_adu.json"])
def test_every_shipped_example_is_structurally_sound(name):
    report = run_preflight(EXAMPLES / name, now=NOW)

    codes = {issue.code for issue in report.errors}
    # Only the two deliberate gates may block: live verification and unmapped kinds.
    assert codes <= {"haeo_type_unverified", "haeo_kind_unmapped"}, codes
    assert Path(report.profile_path).name == name
