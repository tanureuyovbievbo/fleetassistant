"""T-27..T-29: telemetry envelope validation, quality, dedupe."""

from __future__ import annotations

import pytest

from custom_components.fleetassistant.telemetry import DedupeRegistry, summarise, to_envelope, validate_envelope


def payload(**overrides):
    base = {
        "schema_version": 1,
        "site_id": "site_a",
        "deployment_profile": "gateway_primary",
        "seq": 1,
        "captured_at": "2026-07-01T18:00:00+00:00",
        "interval": {"start": "2026-07-01T17:00:00+00:00", "end": "2026-07-01T18:00:00+00:00"},
        "authority": "full",
        "quality": "measured",
        "source": "gateway",
        "metrics": {"import_kw": 1.5, "soc_pct": 62.0},
        "flags": [],
    }
    base.update(overrides)
    return base


def test_valid_payload_has_no_issues() -> None:
    assert validate_envelope(payload()) == []


@pytest.mark.parametrize(
    "overrides,code",
    [
        ({"schema_version": 2}, "schema_version"),
        ({"seq": -1}, "seq"),
        ({"quality": "guessed"}, "choice"),
        ({"authority": "firm"}, "choice"),
        ({"source": "vibes"}, "choice"),
        ({"metrics": {}}, "required"),
        ({"metrics": {"import_kw": "1.5"}}, "metric_value"),
        ({"metrics": {"import_kw": True}}, "metric_value"),
        ({"captured_at": "yesterday"}, "timestamp"),
        ({"interval": {"start": "2026-07-01T18:00:00+00:00", "end": "2026-07-01T17:00:00+00:00"}}, "range"),
        ({"extra_field": 1}, "unknown_key"),
    ],
)
def test_invalid_payloads_are_rejected(overrides, code) -> None:
    codes = {issue.code for issue in validate_envelope(payload(**overrides))}
    assert code in codes


def test_non_mapping_is_rejected() -> None:
    assert validate_envelope([1, 2, 3])[0].code == "type"


def test_firm_requires_measured_full_authority() -> None:
    assert to_envelope(payload()).is_firm()
    assert not to_envelope(payload(authority="coarse")).is_firm()
    assert not to_envelope(payload(quality="estimated")).is_firm()


def test_dedupe_rejects_replays_and_old_sequence_numbers() -> None:
    registry = DedupeRegistry()
    assert registry.accept(payload(seq=5))
    assert not registry.accept(payload(seq=5))
    assert not registry.accept(payload(seq=4))
    assert registry.accept(payload(seq=6))
    assert registry.watermark("site_a") == 6


def test_dedupe_is_per_site() -> None:
    registry = DedupeRegistry()
    assert registry.accept(payload(site_id="a", seq=1))
    assert registry.accept(payload(site_id="b", seq=1))


def test_summary_separates_firm_from_inferred() -> None:
    envelopes = [
        to_envelope(payload(seq=1)),
        to_envelope(payload(seq=2, quality="estimated", source="vendor_cloud", authority="coarse")),
    ]
    summary = summarise(envelopes)
    assert summary["intervals"] == 2
    assert summary["firm_intervals"] == 1
    assert summary["firm_share"] == 0.5
