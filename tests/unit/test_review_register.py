"""The review register is not decoration: code references must resolve to a row."""

from __future__ import annotations

import re
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[2] / "custom_components" / "fleetassistant"
REGISTER = Path(__file__).resolve().parents[2] / "docs" / "verification" / "REVIEW_LATER.md"

REFERENCE = re.compile(r"\bRL-(\d{2})\b")
ROW = re.compile(r"^\|\s*RL-(\d{2})\s*\|", re.MULTILINE)


def _code_references() -> dict[str, str]:
    found: dict[str, str] = {}
    for path in PACKAGE.rglob("*.py"):
        for match in REFERENCE.finditer(path.read_text(encoding="utf-8")):
            found.setdefault(f"RL-{match.group(1)}", path.relative_to(PACKAGE).as_posix())
    return found


def test_register_lists_every_referenced_item():
    rows = {f"RL-{m}" for m in ROW.findall(REGISTER.read_text(encoding="utf-8"))}
    references = _code_references()
    assert references, "no RL-xx references found in the package"
    missing = sorted(set(references) - rows)
    assert not missing, f"code references unregistered items: {missing}"


def test_register_rows_have_a_trigger_and_an_owner():
    for line in REGISTER.read_text(encoding="utf-8").splitlines():
        if not ROW.match(line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        # id | where | gap | trigger | owner
        assert len(cells) == 5, f"row is missing columns: {line}"
        assert cells[2], f"row has no description: {line}"
        assert cells[3], f"row has no trigger: {line}"
        assert cells[4], f"row has no owner: {line}"


def test_register_documents_the_degradation_gaps():
    """ADR-0017 accepted three gaps; the register must keep naming them."""
    text = REGISTER.read_text(encoding="utf-8")
    for item in ("RL-01", "RL-02", "RL-03"):
        assert item in text
    assert "haeo_bridge/plan.py:_degradation_policies" in text
