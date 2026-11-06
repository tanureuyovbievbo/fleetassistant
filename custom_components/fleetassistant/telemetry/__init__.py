"""Telemetry envelope v1: validation and dedupe (D07).

The payload is versioned and deliberately minimal (privacy minimisation, C-18).
Schema keys are ours; they are not vendor shapes and not HA shapes.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..const import TELEMETRY_SCHEMA_VERSION
from ..profile.schema import Issue

QUALITIES = ("measured", "estimated", "stale", "missing")
AUTHORITIES = ("coarse", "full")
SOURCES = ("gateway", "vendor_cloud", "optimizer", "api")

_TOP_KEYS = {
    "schema_version",
    "site_id",
    "deployment_profile",
    "seq",
    "captured_at",
    "interval",
    "authority",
    "quality",
    "source",
    "metrics",
    "plan",
    "flags",
}


@dataclass(frozen=True)
class Envelope:
    schema_version: int
    site_id: str
    deployment_profile: str
    seq: int
    captured_at: datetime
    interval_start: datetime
    interval_end: datetime
    authority: str
    quality: str
    source: str
    metrics: dict[str, float]
    flags: tuple[str, ...] = ()

    def is_firm(self) -> bool:
        """Only measured, full-authority data may back a firm claim (C-12)."""
        return self.authority == "full" and self.quality == "measured"


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def validate_envelope(payload: Any) -> list[Issue]:
    issues: list[Issue] = []
    if not isinstance(payload, dict):
        return [Issue("type", "$", "telemetry payload must be a mapping")]

    for key in payload:
        if key not in _TOP_KEYS:
            issues.append(Issue("unknown_key", f"$.{key}", "not part of telemetry v1"))

    if payload.get("schema_version") != TELEMETRY_SCHEMA_VERSION:
        issues.append(Issue("schema_version", "$.schema_version", f"must be {TELEMETRY_SCHEMA_VERSION}"))

    for key in ("site_id", "deployment_profile"):
        if not isinstance(payload.get(key), str) or not payload.get(key):
            issues.append(Issue("required", f"$.{key}", "must be a non-empty string"))

    seq = payload.get("seq")
    if not isinstance(seq, int) or isinstance(seq, bool) or seq < 0:
        issues.append(Issue("seq", "$.seq", "must be a non-negative integer"))

    captured = _parse_ts(payload.get("captured_at"))
    if captured is None:
        issues.append(Issue("timestamp", "$.captured_at", "must be an ISO-8601 timestamp"))

    interval = payload.get("interval")
    if not isinstance(interval, dict):
        issues.append(Issue("required", "$.interval", "must contain start and end"))
    else:
        start = _parse_ts(interval.get("start"))
        end = _parse_ts(interval.get("end"))
        if start is None or end is None:
            issues.append(Issue("timestamp", "$.interval", "start and end must be ISO-8601"))
        elif end <= start:
            issues.append(Issue("range", "$.interval", "end must be after start"))

    for key, allowed in (("authority", AUTHORITIES), ("quality", QUALITIES), ("source", SOURCES)):
        if payload.get(key) not in allowed:
            issues.append(Issue("choice", f"$.{key}", f"must be one of {', '.join(allowed)}"))

    metrics = payload.get("metrics")
    if not isinstance(metrics, dict) or not metrics:
        issues.append(Issue("required", "$.metrics", "must be a non-empty mapping"))
    else:
        for name, value in metrics.items():
            if not isinstance(name, str) or not name:
                issues.append(Issue("metric_name", "$.metrics", "metric names must be non-empty strings"))
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                issues.append(Issue("metric_value", f"$.metrics.{name}", "must be a finite number"))

    flags = payload.get("flags", [])
    if not isinstance(flags, list) or any(not isinstance(f, str) for f in flags):
        issues.append(Issue("type", "$.flags", "must be a list of strings"))

    return issues


@dataclass
class DedupeRegistry:
    """Rejects replays of (site_id, seq) already accepted by this collector."""

    seen: dict[str, int] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.seen is None:
            self.seen = {}

    def accept(self, payload: dict[str, Any]) -> bool:
        site = str(payload.get("site_id"))
        seq = payload.get("seq")
        if not isinstance(seq, int):
            return False
        watermark = self.seen.get(site, -1)
        if seq <= watermark:
            return False
        self.seen[site] = seq
        return True

    def watermark(self, site_id: str) -> int:
        return self.seen.get(site_id, -1)


def to_envelope(payload: dict[str, Any]) -> Envelope:
    """Convert an already-validated payload into a typed envelope."""
    issues = validate_envelope(payload)
    if issues:
        raise ValueError(f"invalid telemetry envelope: {issues[0]}")
    interval = payload["interval"]
    return Envelope(
        schema_version=int(payload["schema_version"]),
        site_id=str(payload["site_id"]),
        deployment_profile=str(payload["deployment_profile"]),
        seq=int(payload["seq"]),
        captured_at=_parse_ts(payload["captured_at"]),  # type: ignore[arg-type]
        interval_start=_parse_ts(interval["start"]),  # type: ignore[arg-type]
        interval_end=_parse_ts(interval["end"]),  # type: ignore[arg-type]
        authority=str(payload["authority"]),
        quality=str(payload["quality"]),
        source=str(payload["source"]),
        metrics={k: float(v) for k, v in payload["metrics"].items()},
        flags=tuple(payload.get("flags", [])),
    )


def summarise(envelopes: Iterable[Envelope]) -> dict[str, Any]:
    """Single reconciled record inputs: firm share and data quality counts."""
    items = list(envelopes)
    if not items:
        return {"intervals": 0, "firm_intervals": 0, "firm_share": 0.0, "qualities": {}}
    qualities: dict[str, int] = {}
    for item in items:
        qualities[item.quality] = qualities.get(item.quality, 0) + 1
    firm = sum(1 for item in items if item.is_firm())
    return {
        "intervals": len(items),
        "firm_intervals": firm,
        "firm_share": firm / len(items),
        "qualities": qualities,
    }
