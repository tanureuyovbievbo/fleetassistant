"""Profile loading and schema migration (pure Python)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema import SCHEMA_VERSION, Issue, validate_profile


class ProfileError(ValueError):
    """Raised when a profile cannot be loaded or is invalid."""

    def __init__(self, message: str, issues: list[Issue] | None = None) -> None:
        super().__init__(message)
        self.issues = issues or []


def load_profile(path: str | Path) -> dict[str, Any]:
    """Load a YAML or JSON profile and validate it.

    YAML support uses PyYAML, which Home Assistant already ships (C-08). Import
    is deferred so the core works in a bare test environment with JSON only.
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml  # provided by Home Assistant core
        except ImportError as exc:  # pragma: no cover - environment specific
            raise ProfileError("PyYAML is required to load YAML profiles; use JSON instead") from exc
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    profile = migrate(data)
    issues = validate_profile(profile)
    errors = [i for i in issues if i.is_error]
    if errors:
        raise ProfileError(f"profile {p} is invalid ({len(errors)} errors)", issues)
    return profile


def migrate(profile: Any, *, target: int = SCHEMA_VERSION) -> dict[str, Any]:
    """Migrate an older profile document to ``target``.

    v1 is the first schema; there is nothing to migrate yet. Keep the seam so
    older documents fail loudly instead of being silently misinterpreted.
    """
    if not isinstance(profile, dict):
        raise ProfileError("profile must be a mapping")
    version = profile.get("schema_version")
    if version == target:
        return profile
    if isinstance(version, int) and version < target:
        raise ProfileError(
            f"profile schema_version {version} predates v{target} and no migration exists yet; "
            "add a migration step here rather than editing hand-written profiles"
        )
    raise ProfileError(f"unsupported profile schema_version {version!r} (this build understands v{target})")
