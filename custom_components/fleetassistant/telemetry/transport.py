"""Telemetry transport: spool, HTTP/MQTT sinks, and a publisher that never lies.

The producer builds envelopes; this module moves them. Two rules:
1. a payload is validated before it leaves the box;
2. a failed send is spooled, not dropped, and a spool that cannot drain is visible.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from ..const import DOMAIN
from . import validate_envelope

#: A spool longer than this is a fleet problem, not a network blip.
DEFAULT_MAX_SPOOL = 288


@dataclass(frozen=True)
class SendResult:
    """What a sink reports after one attempt."""

    accepted: bool
    detail: str = ""
    status: int | None = None

    @classmethod
    def ok(cls, *, status: int | None = None) -> SendResult:
        return cls(accepted=True, status=status)

    @classmethod
    def retry(cls, detail: str) -> SendResult:
        return cls(accepted=False, detail=detail)

    @classmethod
    def reject(cls, detail: str, *, status: int = 400) -> SendResult:
        """The collector understood us and refused: retrying cannot help."""
        return cls(accepted=False, detail=detail, status=status)


class Sink(Protocol):
    """A destination for one envelope."""

    name: str

    def send(self, payload: Mapping[str, Any]) -> SendResult: ...


@dataclass
class HttpSink:
    """POST JSON to a collector, using an injected poster (no HTTP dependency)."""

    url: str
    poster: Callable[[str, bytes, Mapping[str, str]], tuple[int, str]]
    name: str = "http"
    headers: Mapping[str, str] = field(default_factory=lambda: {"content-type": "application/json"})
    timeout: float = 10.0

    def send(self, payload: Mapping[str, Any]) -> SendResult:
        body = json.dumps(dict(payload), sort_keys=True).encode("utf-8")
        try:
            status, detail = self.poster(self.url, body, self.headers)
        except ConnectionError as err:  # transport down: worth retrying
            return SendResult.retry(f"{self.name}: {err}")
        except Exception as err:  # noqa: BLE001 - an unknown failure must not lose the record
            return SendResult.retry(f"{self.name}: {type(err).__name__}: {err}")
        if 200 <= status < 300:
            return SendResult.ok(status=status)
        if status >= 500 or status == 429:
            return SendResult(accepted=False, detail=f"{self.name}: HTTP {status} {detail}".strip(), status=status)
        return SendResult.reject(f"{self.name}: HTTP {status} {detail}".strip(), status=status)


@dataclass
class MqttSink:
    """Publish JSON on `<prefix>/<site_id>`, using an injected publisher."""

    publisher: Callable[[str, str], None]
    name: str = "mqtt"
    topic_prefix: str = DOMAIN

    def send(self, payload: Mapping[str, Any]) -> SendResult:
        site_id = str(payload.get("site_id", "unknown"))
        topic = f"{self.topic_prefix}/{site_id}"
        try:
            self.publisher(topic, json.dumps(dict(payload), sort_keys=True))
        except Exception as err:  # noqa: BLE001
            return SendResult.retry(f"{self.name}: {type(err).__name__}: {err}")
        return SendResult.ok()


class Spool:
    """A bounded, append-only queue of envelopes that could not be delivered."""

    def __init__(self, path: Path | str, *, max_records: int = DEFAULT_MAX_SPOOL) -> None:
        self.path = Path(path)
        self.max_records = max_records

    def append(self, payload: Mapping[str, Any]) -> int:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        records = self.records()
        records.append(dict(payload))
        overflow = len(records) - self.max_records
        if overflow > 0:
            # Drop the oldest: a stale envelope cannot support a claim anyway.
            records = records[overflow:]
        self.path.write_text(
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in records), encoding="utf-8"
        )
        return overflow if overflow > 0 else 0

    def records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def drain(self, deliver: Callable[[dict[str, Any]], bool]) -> int:
        """Deliver spooled records in order; stop at the first failure."""
        remaining = self.records()
        delivered = 0
        while remaining:
            payload = remaining[0]
            if not deliver(payload):
                break
            remaining.pop(0)
            delivered += 1
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in remaining), encoding="utf-8"
        )
        return delivered

    def __len__(self) -> int:
        return len(self.records())


@dataclass
class PublishReport:
    """Outcome of one publish cycle."""

    sent: int = 0
    spooled: int = 0
    replayed: int = 0
    rejected: list[dict[str, Any]] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    spool_depth: int = 0

    @property
    def ok(self) -> bool:
        return not self.failures and not self.rejected

    def as_dict(self) -> dict[str, Any]:
        return {
            "sent": self.sent,
            "spooled": self.spooled,
            "replayed": self.replayed,
            "rejected": len(self.rejected),
            "failures": list(self.failures),
            "spool_depth": self.spool_depth,
        }


class TelemetryPublisher:
    """Validate, deliver, and spool what did not go through."""

    def __init__(
        self,
        sinks: Iterable[Sink],
        *,
        spool: Spool | None = None,
        record: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self.sinks = list(sinks)
        self.spool = spool
        self.record = record

    def publish(self, payloads: Iterable[Mapping[str, Any]]) -> PublishReport:
        report = PublishReport()
        for payload in payloads:
            issues = validate_envelope(dict(payload))
            if issues:
                report.rejected.append(
                    {"seq": payload.get("seq"), "issues": [issue.as_dict() for issue in issues]}
                )
                continue
            if self._deliver(dict(payload)):
                report.sent += 1
            else:
                report.spooled += 1
                if self.spool is None:
                    report.failures.append("no sink accepted the envelope and no spool is configured")
                else:
                    overflow = self.spool.append(dict(payload))
                    if overflow:
                        report.failures.append(f"spool overflow: dropped {overflow} old envelope(s)")
        if self.spool is not None:
            report.replayed = self.spool.drain(self._deliver)
            report.spool_depth = len(self.spool)
        if self.record is not None:
            self.record("telemetry.publish", report.as_dict())
        return report

    def _deliver(self, payload: dict[str, Any]) -> bool:
        for sink in self.sinks:
            try:
                result = sink.send(payload)
            except Exception:  # noqa: BLE001 - a broken sink must not lose the envelope
                continue
            if result.accepted:
                return True
            if result.status is not None and result.status < 500:
                # A 4xx means this sink refuses this payload; another sink may not.
                continue
        return False


def envelope_sequence(payloads: Iterable[Mapping[str, Any]]) -> list[int]:
    """The sequence numbers a batch carries, for a caller that must persist them."""
    return [int(payload["seq"]) for payload in payloads if "seq" in payload]


def watermark(payload: Mapping[str, Any]) -> datetime | None:
    """The interval end of an envelope, if it has one."""
    interval = payload.get("interval")
    if not isinstance(interval, Mapping):
        return None
    end = interval.get("end")
    if not isinstance(end, str):
        return None
    from datetime import UTC

    try:
        return datetime.fromisoformat(end.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None
