"""Compile a profile + rate provider + overlays into optimizer price inputs.

Output is the seam HAEO consumes: forecast-series price inputs, plus the priced
battery-degradation term (C-14) and any target windows. No regional rule logic
lives here; rule packs only supply providers and overlays.

UNVERIFIED (OQ-007, OQ-012): the exact HAEO input names, segment fields and the
degradation representation. Everything unverified is isolated to constants and
one ``metadata`` block so the spike can correct it in a single place.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from ..const import CONF_PRICE_AUTHORITY
from ..profile.schema import SCHEMA_VERSION
from .overlay import TargetOverlay, apply_overlays, overlay_windows
from .providers import ExportValueCurve, FlatRate, RateProvider, provider_from_profile
from .series import Point, build_series, to_forecast
from .sources import DEFAULT_AUTHORITY, MergedTariff, merge_tariffs, series_from_provider

#: HAEO price input names. UNVERIFIED until the e04 spike (OQ-007).
INPUT_NAMES = {"import": "price_import", "export": "price_export", "degradation": "battery_degradation_cost"}
INPUT_NAMES_VERIFIED = False


def price_entity_id(site_id: str, input_name: str) -> str:
    """Entity id of the forecast sensor we publish for a compiled price input.

    These sensors are ours (the telemetry publisher creates them), so the naming
    is a choice, not a HAEO fact. HAEO's grid element consumes them as
    ``pricing.price_source_target`` / ``price_target_source``; a site that
    already publishes equivalent sensors can override the ids with
    ``compile_plan(..., price_entities=...)``.
    """
    slug = re.sub(r"[^a-z0-9]+", "_", site_id.lower()).strip("_") or "site"
    return f"sensor.fleetassistant_{slug}_{input_name}"


@dataclass
class PriceInputs:
    site_id: str
    horizon_start: datetime
    step_minutes: int
    entities: dict[str, dict[str, object]] = field(default_factory=dict)
    degradation: list[dict[str, Any]] = field(default_factory=list)
    targets: list[dict[str, object]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "site_id": self.site_id,
            "horizon_start": self.horizon_start.isoformat(),
            "step_minutes": self.step_minutes,
            "entities": self.entities,
            "degradation": self.degradation,
            "targets": self.targets,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def compile_price_inputs(
    profile: dict[str, Any],
    *,
    horizon_start: datetime,
    horizon_hours: float = 48.0,
    step_minutes: int = 60,
    overlays: list[TargetOverlay] | None = None,
    provider: RateProvider | None = None,
) -> PriceInputs:
    """Compile price/target/degradation inputs for one site.

    Works with **zero rule packs installed** (C-13): overlays default to empty
    and providers come from the profile's generic pricing block.
    """
    overlays = overlays or []
    if provider is None:
        pricing = profile.get("pricing") or {}
        definition = pricing.get("provider") or {"type": "flat", "currency_per_kwh": 0.0}
        provider = provider_from_profile(definition)

    series = build_series(horizon_start, horizon_hours, step_minutes, provider.price_at)
    adjusted = apply_overlays(series, overlays)

    result = PriceInputs(
        site_id=profile["site"]["id"],
        horizon_start=horizon_start,
        step_minutes=step_minutes,
        metadata={
            "schema_version": SCHEMA_VERSION,
            "provider": provider.name,
            "input_names_verified": INPUT_NAMES_VERIFIED,
            "forecast_format_verified": False,
            "rule_packs": [p.get("id") for p in profile.get("rule_packs", [])],
            "note": "HAEO input names, segment fields and degradation representation are UNVERIFIED (OQ-007, OQ-012)",
        },
    )
    result.entities[INPUT_NAMES["import"]] = to_forecast(adjusted)

    # Export: v1 has no regional export curve. If the provider exposes one we
    # use it; otherwise export value mirrors import price only when the profile
    # opts in, and is otherwise zero (never silently assumed profitable).
    export_value = _export_value_for(profile)
    if export_value is not None:
        export_points = build_series(horizon_start, horizon_hours, step_minutes, export_value)
        result.entities[INPUT_NAMES["export"]] = to_forecast(apply_overlays(export_points, overlays))
    else:
        result.warnings.append(
            "no export value configured: export price defaults to 0.0 (add an export value curve via a rule pack)"
        )
        result.entities[INPUT_NAMES["export"]] = to_forecast(
            [Point(p.ts, 0.0) for p in adjusted]
        )

    result.degradation = _degradation_inputs(profile)
    if any(item["required"] and item["currency_per_kwh"] <= 0 for item in result.degradation):
        result.warnings.append("battery degradation cost is zero or missing (C-14 violation)")

    result.targets = overlay_windows(overlays)
    return result


def _export_value_for(profile: dict[str, Any]):
    provider = (profile.get("pricing") or {}).get("provider") or {}
    if provider.get("type") == "dynamic" and provider.get("export_series"):
        series = provider["export_series"]
        points = [Point(ts=datetime.fromisoformat(p["datetime"].replace("Z", "+00:00")), value=float(p["value"])) for p in series]
        from .providers import DynamicSeries

        dynamic = DynamicSeries(points=tuple(points))
        return dynamic.price_at
    return None


def _degradation_inputs(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """One degradation input per battery element. Required, never silent (C-14)."""
    items: list[dict[str, Any]] = []
    for system in profile.get("systems", []):
        for element in system.get("elements", []):
            if element.get("kind") != "battery":
                continue
            cost = element.get("degradation_cost") or {}
            items.append(
                {
                    "system_id": system.get("id"),
                    "element": element.get("id"),
                    "input": INPUT_NAMES["degradation"],
                    "currency_per_kwh": float(cost.get("currency_per_kwh", 0.0)),
                    "source": cost.get("source", ""),
                    "required": True,
                    "representation_verified": False,
                }
            )
    return items


def horizon_end(result: PriceInputs, horizon_hours: float) -> datetime:
    return result.horizon_start + timedelta(hours=horizon_hours)


#: How far ahead we publish prices. HAEO's largest preset is 7 days; 48 h covers a
#: 5-day default horizon with slack and is cheap to rebuild.
PRICE_HORIZON_HOURS = 48.0
PRICE_STEP_MINUTES = 60


def price_authority(profile: dict[str, Any], options: dict[str, Any] | None = None) -> str:
    """Authority for the price merge: options > profile > deployment default."""
    explicit = str((options or {}).get(CONF_PRICE_AUTHORITY) or "").strip()
    if explicit:
        return explicit
    configured = (profile.get("pricing") or {}).get("authority")
    if configured:
        return str(configured)
    deployment = (profile.get("deployment") or {}).get("profile", "gateway_primary")
    return DEFAULT_AUTHORITY.get(str(deployment), "user")


def resolve_tariffs(
    profile: dict[str, Any],
    options: dict[str, Any] | None = None,
    *,
    now: datetime | None = None,
    cloud: Any = None,
    horizon_hours: float = PRICE_HORIZON_HOURS,
    step_minutes: int = PRICE_STEP_MINUTES,
) -> dict[str, MergedTariff]:
    """Build the merged import/export prices we publish for HAEO.

    ``cloud`` accepts a :class:`~.sources.SeriesResult` (a caller that already
    fetched, e.g. the future cloud provider at RL-20). Without one, the user
    schedule is the only source and an authority of ``cloud`` degrades visibly.
    """
    moment = now or datetime.now(UTC)
    start = moment.replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=horizon_hours)
    site_id = str(profile["site"]["id"])
    pricing = profile.get("pricing") or {}
    authority = price_authority(profile, options)

    user_import = series_from_provider(
        provider_from_profile(pricing["provider"]),
        start=start,
        end=end,
        step_minutes=step_minutes,
        quality="entered",
    )
    tariffs = {
        INPUT_NAMES["import"]: merge_tariffs(
            site_id=site_id, cloud=cloud, user=user_import, authority=authority, now=moment
        )
    }

    export_config = pricing.get("export")
    if isinstance(export_config, dict) and "currency_per_kwh" in export_config:
        export_provider: RateProvider = ExportValueCurve(
            currency_per_kwh=float(export_config["currency_per_kwh"]),
            hour_multipliers=tuple(export_config.get("hour_multipliers") or ()),
        )
        export_series = series_from_provider(
            export_provider, start=start, end=end, step_minutes=step_minutes, quality="entered"
        )
    else:
        export_series = series_from_provider(
            FlatRate(0.0, name="no_export_value"),
            start=start,
            end=end,
            step_minutes=step_minutes,
            quality="fallback",
            warnings=("no export value configured: exports are valued at 0.0 (add an export curve)",),
        )
    tariffs[INPUT_NAMES["export"]] = merge_tariffs(
        site_id=site_id, cloud=None, user=export_series, authority=authority, now=moment
    )
    return tariffs
