"""Shared test helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = REPO_ROOT / "site_profiles" / "examples"


def example(name: str) -> dict[str, Any]:
    path = EXAMPLES / name
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    import yaml

    return yaml.safe_load(text)


def deep_copy(profile: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(profile))
