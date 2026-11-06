"""The mechanical constraint probes must pass on this repo and catch violations."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from helpers import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "tools"))
from check_boundaries import check_repo  # noqa: E402


def test_repository_is_clean() -> None:
    assert check_repo(REPO_ROOT) == []


def test_probe_catches_homeassistant_import_in_core(tmp_path: Path) -> None:
    pkg = tmp_path / "custom_components" / "fleetassistant"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({"domain": "fleetassistant", "requirements": []}), encoding="utf-8")
    (pkg / "evil.py").write_text("from homeassistant.core import HomeAssistant\n", encoding="utf-8")
    violations = check_repo(tmp_path)
    assert any("imports homeassistant at module level" in v for v in violations)


def test_probe_catches_declared_requirements(tmp_path: Path) -> None:
    pkg = tmp_path / "custom_components" / "fleetassistant"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(
        json.dumps({"domain": "fleetassistant", "requirements": ["highspy>=1.15.1"]}), encoding="utf-8"
    )
    violations = check_repo(tmp_path)
    assert any("must not declare requirements" in v for v in violations)


def test_probe_catches_haeo_import_outside_bridge(tmp_path: Path) -> None:
    pkg = tmp_path / "custom_components" / "fleetassistant"
    (pkg / "pricing").mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({"domain": "fleetassistant", "requirements": []}), encoding="utf-8")
    (pkg / "pricing" / "leak.py").write_text("from custom_components.haeo import config_flow\n", encoding="utf-8")
    violations = check_repo(tmp_path)
    assert any("only haeo_bridge/ may" in v for v in violations)


def test_package_imports_without_home_assistant() -> None:
    import custom_components.fleetassistant as package

    assert package.__version__ == "0.1.0"
    assert "homeassistant" not in sys.modules
