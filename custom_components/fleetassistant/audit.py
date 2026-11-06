"""Append-only, hash-chained audit log (C-18).

Every control decision — applied, clamped, skipped, or rejected — appends one
record. Records are chained by SHA-256 so silent edits or deletions break
``verify()``. Storage is a JSONL file or memory (tests); a WORM sink is a fleet
concern (D08).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

GENESIS = "0" * 64


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


@dataclass(frozen=True)
class AuditRecord:
    seq: int
    ts: str
    kind: str
    payload: dict[str, Any]
    prev_hash: str
    hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "ts": self.ts,
            "kind": self.kind,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditRecord:
        return cls(
            seq=int(data["seq"]),
            ts=str(data["ts"]),
            kind=str(data["kind"]),
            payload=dict(data["payload"]),
            prev_hash=str(data["prev_hash"]),
            hash=str(data["hash"]),
        )


def _digest(seq: int, ts: str, kind: str, payload: dict[str, Any], prev_hash: str) -> str:
    body = _canonical({"seq": seq, "ts": ts, "kind": kind, "payload": payload, "prev_hash": prev_hash})
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


class AuditLog:
    """Append-only log. One instance per site."""

    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path is not None else None
        self._records: list[AuditRecord] = []
        if self._path is not None and self._path.exists():
            for line in self._path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self._records.append(AuditRecord.from_dict(json.loads(line)))

    def append(self, kind: str, payload: dict[str, Any], ts: datetime | None = None) -> AuditRecord:
        stamp = (ts or datetime.now(UTC)).astimezone(UTC).isoformat()
        seq = len(self._records)
        prev_hash = self._records[-1].hash if self._records else GENESIS
        record = AuditRecord(
            seq=seq,
            ts=stamp,
            kind=kind,
            payload=payload,
            prev_hash=prev_hash,
            hash=_digest(seq, stamp, kind, payload, prev_hash),
        )
        self._records.append(record)
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(_canonical(record.as_dict()) + "\n")
        return record

    def records(self) -> tuple[AuditRecord, ...]:
        return tuple(self._records)

    def __len__(self) -> int:
        return len(self._records)

    def verify(self) -> bool:
        """Recompute the chain. False means the log was altered."""
        prev_hash = GENESIS
        for index, record in enumerate(self._records):
            if record.seq != index or record.prev_hash != prev_hash:
                return False
            expected = _digest(record.seq, record.ts, record.kind, record.payload, record.prev_hash)
            if record.hash != expected:
                return False
            prev_hash = record.hash
        return True

    def tail(self, count: int = 20) -> Iterable[AuditRecord]:
        return tuple(self._records[-count:])
