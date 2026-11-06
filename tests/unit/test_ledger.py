"""T-26: commitments ledger prevents double counting (C-16)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from custom_components.fleetassistant.ledger import Commitment, CommitmentsLedger, LedgerError, max_exposure

BASE = datetime(2026, 7, 1, 18, 0, tzinfo=UTC)


def _commitment(cid: str, program: str, start_h: int, hours: int, kw: float, authority: str = "full") -> Commitment:
    return Commitment(
        commitment_id=cid,
        program_id=program,
        start=BASE + timedelta(hours=start_h),
        end=BASE + timedelta(hours=start_h + hours),
        kw=kw,
        authority=authority,  # type: ignore[arg-type]
    )


def test_non_overlapping_commitments_are_allowed() -> None:
    ledger = CommitmentsLedger("site", qualified_capacity_kw=10.0)
    ledger.add(_commitment("a", "program_1", 0, 1, 8.0))
    ledger.add(_commitment("b", "program_2", 2, 1, 8.0))
    assert len(ledger.as_list()) == 2


def test_overlapping_commitments_across_programs_are_rejected() -> None:
    ledger = CommitmentsLedger("site", qualified_capacity_kw=10.0)
    ledger.add(_commitment("a", "program_1", 0, 2, 6.0))
    with pytest.raises(LedgerError, match="over-commitment"):
        ledger.add(_commitment("b", "program_2", 1, 2, 6.0))


def test_exposure_reports_peak_in_window() -> None:
    ledger = CommitmentsLedger("site", qualified_capacity_kw=20.0)
    ledger.add(_commitment("a", "p1", 0, 4, 5.0))
    ledger.add(_commitment("b", "p2", 1, 2, 7.0))
    assert ledger.exposure(BASE, BASE + timedelta(hours=4)) == 12.0


def test_duplicate_ids_are_rejected() -> None:
    ledger = CommitmentsLedger("site", 10.0)
    ledger.add(_commitment("a", "p1", 0, 1, 2.0))
    with pytest.raises(LedgerError, match="already exists"):
        ledger.add(_commitment("a", "p1", 5, 1, 2.0))


def test_firm_commitment_requires_full_authority() -> None:
    with pytest.raises(LedgerError, match="full authority"):
        Commitment("a", "p1", BASE, BASE + timedelta(hours=1), 5.0, authority="coarse", tier="firm")


def test_best_effort_cloud_commitment_is_allowed() -> None:
    commitment = Commitment("a", "p1", BASE, BASE + timedelta(hours=1), 5.0, authority="coarse")
    assert commitment.tier == "best_effort"


def test_empty_ledger_has_zero_exposure() -> None:
    assert max_exposure([]) == 0.0


def test_remove_returns_the_commitment() -> None:
    ledger = CommitmentsLedger("site", 10.0)
    ledger.add(_commitment("a", "p1", 0, 1, 2.0))
    assert ledger.remove("a").commitment_id == "a"
    with pytest.raises(LedgerError):
        ledger.remove("a")


def test_two_programs_cannot_hold_the_same_capability_over_the_same_window():
    now = datetime(2026, 11, 6, 18, 0, tzinfo=UTC)
    ledger = CommitmentsLedger("site_a", 10.0)
    ledger.add(Commitment("c1", "elrp", now, now + timedelta(hours=1), 4.0, "full", capability="set_export_limit"))

    conflicts = ledger.conflicts(program_id="vpp", start=now, end=now + timedelta(minutes=30), capability="set_export_limit")

    assert [c.program_id for c in conflicts] == ["elrp"]


def test_the_same_program_may_refresh_its_own_window():
    now = datetime(2026, 11, 6, 18, 0, tzinfo=UTC)
    ledger = CommitmentsLedger("site_a", 10.0)
    ledger.add(Commitment("c1", "elrp", now, now + timedelta(hours=1), 4.0, "full", capability="set_export_limit"))

    assert ledger.conflicts(program_id="elrp", start=now, end=now + timedelta(hours=1), capability="set_export_limit") == []


def test_a_different_capability_is_not_a_conflict():
    now = datetime(2026, 11, 6, 18, 0, tzinfo=UTC)
    ledger = CommitmentsLedger("site_a", 10.0)
    ledger.add(Commitment("c1", "elrp", now, now + timedelta(hours=1), 4.0, "full", capability="set_export_limit"))

    assert ledger.conflicts(program_id="vpp", start=now, end=now + timedelta(hours=1), capability="set_battery_target") == []


def test_headroom_shrinks_as_exposure_grows():
    now = datetime(2026, 11, 6, 18, 0, tzinfo=UTC)
    ledger = CommitmentsLedger("site_a", 10.0)
    ledger.add(Commitment("c1", "elrp", now, now + timedelta(hours=1), 4.0, "full"))

    assert ledger.headroom(now, now + timedelta(minutes=30)) == 6.0
    ledger.add(Commitment("c2", "vpp", now, now + timedelta(minutes=30), 6.0, "full"))
    assert ledger.headroom(now, now + timedelta(minutes=15)) == 0.0

