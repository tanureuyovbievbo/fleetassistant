"""The published JSON Schema and the executable validator must not drift."""

from __future__ import annotations

import json

import pytest
from helpers import REPO_ROOT

from custom_components.fleetassistant.profile.loader import ProfileError, load_profile
from custom_components.fleetassistant.profile.schema import (
    _TOP_LEVEL_KEYS,
    CAPABILITY_UNITS,
    ELEMENT_KINDS,
    SCHEMA_VERSION,
)

SCHEMA_PATH = REPO_ROOT / "site_profiles" / "schema" / "site-profile.v1.schema.json"
INVALID = REPO_ROOT / "site_profiles" / "examples" / "invalid"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_schema_file_is_draft_2020_12(schema) -> None:
    assert schema["$schema"].endswith("2020-12/schema")


def test_top_level_keys_match_validator(schema) -> None:
    assert set(schema["properties"]) == set(_TOP_LEVEL_KEYS)
    assert set(schema["required"]) <= set(_TOP_LEVEL_KEYS)


def test_schema_pins_the_same_version(schema) -> None:
    assert schema["properties"]["schema_version"]["const"] == SCHEMA_VERSION


def test_every_element_kind_is_described(schema) -> None:
    described = set(schema["$defs"]["element"]["properties"]["kind"]["enum"])
    assert described == set(ELEMENT_KINDS)


def test_every_capability_and_unit_is_described(schema) -> None:
    control = schema["$defs"]["control"]["properties"]
    assert set(control["capability"]["enum"]) == set(CAPABILITY_UNITS)
    assert set(control["unit"]["enum"]) == set(CAPABILITY_UNITS.values())


@pytest.mark.parametrize(
    "name,code",
    [
        ("dangling_reference.json", "dangling_reference"),
        ("battery_without_degradation.json", "required"),
        ("haeo_name_leak.json", "haeo_leak"),
        ("cloud_primary_local_control.json", "authority_mismatch"),
    ],
)
def test_invalid_fixtures_fail_with_a_reason(name: str, code: str) -> None:
    with pytest.raises(ProfileError) as caught:
        load_profile(INVALID / name)
    assert code in {issue.code for issue in caught.value.issues}
