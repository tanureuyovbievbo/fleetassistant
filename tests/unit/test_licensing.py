"""The repository licence is a claim; these tests keep it honest.

Apache-2.0 §4(d) requires the NOTICE to travel with the work, and C-21 requires that
we never imply an affiliation we do not have. Both are checkable.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def _without_note(text: str) -> tuple[str, list[str]]:
    """Split a leading '#' note block from the licence text it precedes."""
    lines = text.splitlines()
    note: list[str] = []
    while lines and lines[0].startswith("#"):
        note.append(lines.pop(0))
    return chr(10).join(lines), note


def test_license_carries_a_removal_note_before_the_canonical_text():
    """RL-33: the prefix is a reminder, and it must be visibly removable."""
    _, note = _without_note(_read("LICENSE"))
    joined = chr(10).join(note).lower()

    assert note, "LICENSE lost its edit-later note"
    assert "rl-33" in joined
    assert "must not be edited" in joined
    assert "copyright holder" in joined


def test_license_is_the_apache_2_0_text():
    licence, _ = _without_note(_read("LICENSE"))

    assert licence.lstrip().startswith("Apache License")
    assert "Version 2.0, January 2004" in licence
    assert "TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION" in licence
    assert "END OF TERMS AND CONDITIONS" in licence
    # §3 and §4 are the clauses the ADR leans on; a truncated file would drop them.
    assert "Grant of Patent License" in licence
    assert "Redistribution" in licence
    assert "Trademarks" in licence


def test_notice_names_the_composed_works_and_their_licences():
    notice = _read("NOTICE")

    assert "fleetassistant" in notice
    assert "Apache License, Version 2.0" in notice
    assert "HAEO" in notice and "MIT License" in notice
    assert "Home Assistant Core" in notice


def test_notice_makes_no_affiliation_claim():
    notice = _read("NOTICE").lower()

    for forbidden in ("certified", "in partnership", "member of", "endorsed by the"):
        assert forbidden not in notice or "not affiliated" in notice
    assert "not affiliated" in notice


def test_notice_copyright_holder_is_an_explicit_placeholder():
    """Never invent a legal entity; an empty holder must look empty."""
    first_lines = _read("NOTICE").splitlines()[:2]
    holder = first_lines[1]

    assert holder.lower().startswith("copyright 2026")
    assert "placeholder" in holder.lower()
    assert "the fleetassistant contributors" not in holder.lower()


def test_pyproject_declares_the_same_licence_as_the_adr():
    project = tomllib.loads(_read("pyproject.toml"))["project"]
    adr = _read("specs/adr/ADR-0023-apache-2-0-license.md")

    assert project["license"] == "Apache-2.0"
    assert "Apache-2.0" in adr
    assert "accepted" in adr


def test_no_upstream_source_is_vendored():
    """C-05: we compose HAEO over its flows, we never copy it in."""
    package = ROOT / "custom_components" / "fleetassistant"

    for path in package.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "custom_components.haeo" not in text, path
        assert "from homeassistant.components.haeo" not in text, path


def test_device_pack_licence_fields_exist_so_a_gpl_integration_is_visible():
    """C-19: a GPL-3 device integration must be visible before it enters a paid fleet."""
    from dataclasses import fields

    from custom_components.fleetassistant.device_packs import DevicePack

    names = {field.name for field in fields(DevicePack)}
    assert {"licence_note", "tos_note", "sources", "verified"} <= names
