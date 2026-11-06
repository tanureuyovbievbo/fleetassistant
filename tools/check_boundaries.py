"""Constraint probes (C-01..C-24) that can be checked mechanically.

Run: python tools/check_boundaries.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PACKAGE = Path("custom_components") / "fleetassistant"
HA_MODULE_LEVEL_ALLOWED = {
    "__init__.py",
    "runtime.py",
    "config_flow.py",
    "diagnostics.py",
    "sensor.py",  # entities are HA objects; the values they expose are computed in pricing/
}

#: Modules (beyond the package root) allowed to import Home Assistant: the HAEO
#: bridge (it speaks HA's flow API) and the adapter glue that turns a capability
#: into a service call. Everything else stays importable without HA, so tests run
#: on a laptop and the core has no hidden lifecycle.
HA_MODULE_LEVEL_ALLOWED_PATHS = {"adapters/ha_caller.py"}
HA_IMPORT = re.compile(r"^\s*(?:from|import)\s+homeassistant\b", re.MULTILINE)
HAEO_IMPORT = re.compile(r"^\s*(?:from|import)\s+(?:custom_components\.haeo|\.\.haeo)\b", re.MULTILINE)
SERVICE_CALL = re.compile(r"services\.async_call\(")
STORAGE_WRITE = re.compile(r"\.storage")


def check_repo(root: Path) -> list[str]:
    """Return human-readable violations. Empty list == clean."""
    violations: list[str] = []
    package = root / PACKAGE
    if not package.is_dir():
        return [f"missing package directory: {PACKAGE}"]

    manifest = package / "manifest.json"
    if manifest.is_file():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if data.get("requirements"):
            violations.append(
                "C-08: manifest.json must not declare requirements "
                f"(found {data['requirements']}); vendor code or document ops steps instead"
            )
        if data.get("domain") != "fleetassistant":
            violations.append(f"C-03: manifest domain must be fleetassistant (found {data.get('domain')!r})")
    else:
        violations.append("C-03: manifest.json is missing")

    for path in sorted(package.rglob("*.py")):
        rel = path.relative_to(package)
        text = path.read_text(encoding="utf-8")
        area = rel.parts[0] if len(rel.parts) > 1 else ""

        if area != "haeo_bridge" and HAEO_IMPORT.search(text):
            violations.append(f"C-06: {rel} imports HAEO internals; only haeo_bridge/ may")

        if STORAGE_WRITE.search(text):
            violations.append(f"C-06: {rel} references .storage; HAEO storage is off-limits")

        allowed_path = rel.as_posix() in HA_MODULE_LEVEL_ALLOWED_PATHS
        if HA_IMPORT.search(text) and rel.name not in HA_MODULE_LEVEL_ALLOWED and not allowed_path and area != "haeo_bridge":
            violations.append(f"C-08: {rel} imports homeassistant at module level; keep core pure Python")

        if SERVICE_CALL.search(text) and area != "adapters":
            violations.append(f"C-09: {rel} calls device services outside adapters/")

    return violations


def main(argv: list[str] | None = None) -> int:
    root = Path(argv[1] if argv and len(argv) > 1 else ".").resolve()
    violations = check_repo(root)
    if violations:
        print("constraint violations:")
        for violation in violations:
            print(f"  - {violation}")
        return 1
    print("constraint probes: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
