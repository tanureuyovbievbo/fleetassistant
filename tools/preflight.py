"""Offline preflight for a site profile.

Runs everything that does not need a live Home Assistant: schema validation, plan
compilation, referential integrity, tariff resolution and the reference inventory.
Exit code 0 means the profile is structurally applyable; it does not mean the site
will converge (that needs HA).

    python tools/preflight.py site_profiles/examples/solark_gateway_primary.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components"))

from fleetassistant.device_packs import controls_from_pack, load_packs  # noqa: E402
from fleetassistant.haeo_bridge import fields  # noqa: E402
from fleetassistant.haeo_bridge.plan import compile_plan  # noqa: E402
from fleetassistant.haeo_bridge.prevalidate import prevalidate  # noqa: E402
from fleetassistant.pricing.compiler import resolve_tariffs  # noqa: E402
from fleetassistant.profile.loader import ProfileError, load_profile  # noqa: E402
from fleetassistant.profile.schema import Issue, validate_profile  # noqa: E402
from fleetassistant.references import collect_references  # noqa: E402


@dataclass
class Preflight:
    profile_path: str
    site_id: str = ""
    deployment_profile: str = ""
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)
    hubs: int = 0
    elements: int = 0
    controls: int = 0
    references: list[str] = field(default_factory=list)
    tariffs: dict[str, Any] = field(default_factory=dict)
    topology: str = ""

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile_path,
            "site_id": self.site_id,
            "deployment_profile": self.deployment_profile,
            "ok": self.ok,
            "hubs": self.hubs,
            "elements": self.elements,
            "controls": self.controls,
            "topology": self.topology,
            "references": self.references,
            "tariffs": self.tariffs,
            "errors": [issue.as_dict() for issue in self.errors],
            "warnings": [issue.as_dict() for issue in self.warnings],
        }


def run_preflight(
    profile_path: Path,
    *,
    packs_root: Path | None = None,
    now: datetime | None = None,
    horizon_hours: float = 48.0,
) -> Preflight:
    now = now or datetime.now(UTC)
    result = Preflight(profile_path=str(profile_path))

    try:
        profile = load_profile(profile_path)
    except ProfileError as err:
        result.errors.extend(err.issues or [Issue("profile", str(profile_path), str(err), "error")])
        return result

    result.site_id = str((profile.get("site") or {}).get("id", ""))
    result.deployment_profile = str((profile.get("deployment") or {}).get("profile", ""))

    issues = validate_profile(profile)
    result.errors.extend(issue for issue in issues if issue.is_error)
    result.warnings.extend(issue for issue in issues if not issue.is_error)

    if packs_root is not None:
        packs, pack_issues = load_packs(packs_root)
        result.warnings.extend(issue for issue in pack_issues if not issue.is_error)
        result.errors.extend(issue for issue in pack_issues if issue.is_error)
        for brand_id, pack in packs.items():
            result.warnings.append(
                Issue(
                    "pack_available",
                    f"device_packs.{brand_id}",
                    f"pack {brand_id} offers {', '.join(pack.capabilities())} "
                    f"({'cloud' if pack.is_cloud else 'local'}, verified={pack.verified})",
                    "warning",
                )
            )
            if pack.is_cloud and result.deployment_profile == "gateway_primary":
                result.errors.append(
                    Issue(
                        "pack_authority",
                        f"device_packs.{brand_id}",
                        f"{brand_id} is a cloud pack and cannot serve a gateway_primary site (C-12)",
                        "error",
                    )
                )
            controls_from_pack(pack, element_id="preflight")

    if result.errors:
        return result

    plan = compile_plan(profile)
    result.hubs = len(plan.hubs)
    result.elements = len(plan.elements)
    result.controls = len(profile.get("controls") or [])
    connections = {element.connection for element in plan.elements if element.connection}
    if fields.HUB_SWITCHBOARD in connections:
        # Resolved against the live hub at apply time (ADR-0025); offline we can
        # only report which symbolic target the plan carries.
        result.topology = "<hub switchboard>"
    plan_issues = prevalidate(plan)
    result.errors.extend(issue for issue in plan_issues if issue.is_error)
    result.warnings.extend(issue for issue in plan_issues if not issue.is_error)

    published = {entity_id for entity_id in _published(profile, now, horizon_hours)}
    result.references = sorted(
        {reference.entity_id for reference in collect_references(profile, published=published)}
    )

    try:
        tariffs = resolve_tariffs(profile, {}, now=now, horizon_hours=horizon_hours)
    except Exception as err:  # a pricing provider misconfiguration must not crash preflight
        result.errors.append(Issue("pricing", "pricing", f"could not resolve tariffs: {err}", "error"))
        return result
    for name, tariff in tariffs.items():
        result.tariffs[name] = {
            "authority": tariff.authority,
            "points": len(tariff.points),
            "degraded": len(tariff.stale),
            "missing": len(tariff.missing),
            "sources": tariff.sources,
        }
        if tariff.missing:
            result.warnings.append(
                Issue("price_missing", f"pricing.{name}", f"{len(tariff.missing)} period(s) have no price", "warning")
            )
    return result


def _published(profile: dict[str, Any], now: datetime, horizon_hours: float) -> set[str]:
    try:
        return set(resolve_tariffs(profile, {}, now=now, horizon_hours=horizon_hours))
    except Exception:
        return set()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline preflight for a fleetassistant site profile.")
    parser.add_argument("profile", type=Path, help="site profile (.json or .yaml)")
    parser.add_argument("--packs", type=Path, default=None, help="device pack directory to include in the report")
    parser.add_argument("--horizon-hours", type=float, default=48.0)
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    args = parser.parse_args(argv)

    report = run_preflight(args.profile, packs_root=args.packs, horizon_hours=args.horizon_hours)
    payload = report.as_dict()

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"profile          {payload['profile']}")
        print(f"site             {payload['site_id']} ({payload['deployment_profile']})")
        print(f"plan             {payload['hubs']} hub(s), {payload['elements']} element(s), {payload['controls']} control(s)")
        if payload["topology"]:
            print(f"topology         connected elements -> {payload['topology']} (resolved at apply)")
        for name, tariff in payload["tariffs"].items():
            print(
                f"price {name:<14} {tariff['points']} point(s), authority {tariff['authority']}, "
                f"{tariff['degraded']} degraded, {tariff['missing']} missing"
            )
        if payload["references"]:
            print("references")
            for entity_id in payload["references"]:
                print(f"  - {entity_id}")
        for issue in payload["warnings"]:
            print(f"WARNING {issue['code']:<24} {issue['path']}: {issue['message']}")
        for issue in payload["errors"]:
            print(f"ERROR   {issue['code']:<24} {issue['path']}: {issue['message']}")
        print("result           " + ("READY" if payload["ok"] else "BLOCKED"))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
