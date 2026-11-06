"""Transport: a failed send is spooled, never dropped, and a bad payload never leaves."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from custom_components.fleetassistant.telemetry import validate_envelope
from custom_components.fleetassistant.telemetry.producer import Sample, TelemetryProducer
from custom_components.fleetassistant.telemetry.transport import (
    HttpSink,
    MqttSink,
    PublishReport,
    Spool,
    TelemetryPublisher,
    watermark,
)

NOW = datetime(2026, 11, 6, 18, 0, tzinfo=UTC)


class FakeSink:
    def __init__(self, name: str = "fake", *, accept=True, status: int | None = None, fail: Exception | None = None):
        self.name = name
        self.accept = accept
        self.status = status
        self.fail = fail
        self.payloads: list[dict] = []

    def send(self, payload):
        from custom_components.fleetassistant.telemetry.transport import SendResult

        if self.fail is not None:
            raise self.fail
        self.payloads.append(dict(payload))
        if self.accept:
            return SendResult.ok(status=200)
        return SendResult(accepted=False, detail="nope", status=self.status)


def _payloads(count: int = 1) -> list[dict]:
    """`count` distinct envelopes: the producer groups by quality/source/authority."""
    producer = TelemetryProducer(site_id="site_a", deployment_profile="gateway_primary")
    producer.start(NOW - timedelta(minutes=5))
    qualities = ("estimated", "measured", "stale")
    for index in range(count):
        producer.observe(Sample(f"grid.p{index}", float(index), quality=qualities[index % len(qualities)]))
    return producer.build(now=NOW)


def test_a_valid_envelope_is_delivered_to_the_first_accepting_sink():
    sink = FakeSink()
    report = TelemetryPublisher([sink]).publish(_payloads())

    assert (report.sent, report.spooled, report.ok) == (1, 0, True)
    assert sink.payloads[0]["site_id"] == "site_a"


def test_an_invalid_envelope_is_rejected_and_never_sent():
    sink = FakeSink()
    payload = _payloads()[0]
    payload["quality"] = "hopeful"

    report = TelemetryPublisher([sink]).publish([payload])

    assert report.sent == 0
    paths = {issue["path"] for issue in report.rejected[0]["issues"]}
    assert report.rejected and any("quality" in path for path in paths)
    assert sink.payloads == []


def test_a_failed_send_is_spooled_and_drained_on_the_next_cycle(tmp_path):
    spool = Spool(tmp_path / "telemetry.jsonl")
    dead = FakeSink("dead", accept=False, status=503)
    publisher = TelemetryPublisher([dead], spool=spool)

    first = publisher.publish(_payloads())
    assert first.spooled == 1
    assert len(spool) == 1
    assert first.spool_depth == 1

    dead.accept, dead.status = True, 200
    second = publisher.publish([])

    assert second.replayed == 1
    assert len(spool) == 0
    assert second.spool_depth == 0


def test_without_a_spool_a_failed_send_is_reported_not_hidden():
    report = TelemetryPublisher([FakeSink(accept=False, status=503)]).publish(_payloads())
    assert report.spooled == 1
    assert "no sink accepted" in report.failures[0]
    assert report.ok is False


def test_the_spool_is_bounded_and_drops_the_oldest_envelope(tmp_path):
    spool = Spool(tmp_path / "telemetry.jsonl", max_records=2)
    publisher = TelemetryPublisher([FakeSink(accept=False, status=503)], spool=spool)

    report = publisher.publish(_payloads(count=3))

    assert len(spool) == 2
    assert report.spooled == 3
    assert any("overflow" in failure for failure in report.failures)
    # seq 1 and 2 survive; seq 0 was dropped as the oldest.
    assert [record["seq"] for record in spool.records()] == [1, 2]


def test_a_drain_stops_at_the_first_failure_and_keeps_the_rest(tmp_path):
    spool = Spool(tmp_path / "telemetry.jsonl")
    payloads = _payloads(count=3)
    for payload in payloads:
        spool.append(payload)

    attempts: list[int] = []

    def deliver(payload: dict) -> bool:
        attempts.append(int(payload["seq"]))
        return len(attempts) < 2

    assert spool.drain(deliver) == 1
    assert [record["seq"] for record in spool.records()] == [1, 2]


def test_the_spool_ignores_a_corrupt_line_instead_of_crashing(tmp_path):
    path = tmp_path / "telemetry.jsonl"
    path.write_text('{"seq": 0}\nnot json\n{"seq": 1}\n', encoding="utf-8")
    assert [record["seq"] for record in Spool(path).records()] == [0, 1]


def test_a_client_error_on_one_sink_still_tries_the_next():
    rejecting = FakeSink("rejecting", accept=False, status=400)
    accepting = FakeSink("accepting")
    report = TelemetryPublisher([rejecting, accepting]).publish(_payloads())

    assert report.sent == 1
    assert accepting.payloads


def test_a_transport_exception_is_a_failure_not_a_crash():
    report = TelemetryPublisher([FakeSink(fail=ConnectionError("socket closed"))]).publish(_payloads())
    assert report.spooled == 1


def test_http_sink_accepts_2xx_retries_5xx_and_rejects_4xx():
    posted: list[tuple] = []

    def poster(url, body, headers):
        posted.append((url, body, headers))
        return (204 if "ok" in url else (503 if "down" in url else 422)), "detail"

    ok = HttpSink("https://collector/ok", poster).send({"a": 1})
    down = HttpSink("https://collector/down", poster).send({"a": 1})
    bad = HttpSink("https://collector/bad", poster).send({"a": 1})

    assert ok.accepted and ok.status == 204
    assert not down.accepted and down.status == 503
    assert not bad.accepted and bad.status == 422
    assert json.loads(posted[0][1]) == {"a": 1}
    assert posted[0][2]["content-type"] == "application/json"


def test_http_sink_turns_a_connection_error_into_a_retry():
    def poster(url, body, headers):
        raise ConnectionError("refused")

    result = HttpSink("https://collector", poster).send({"a": 1})
    assert result.accepted is False
    assert result.status is None
    assert "refused" in result.detail


def test_mqtt_sink_publishes_on_the_site_topic():
    published: list[tuple[str, str]] = []
    sink = MqttSink(lambda topic, payload: published.append((topic, payload)))

    result = sink.send(_payloads()[0])

    assert result.accepted
    assert published[0][0] == "fleetassistant/site_a"
    assert json.loads(published[0][1])["seq"] == 0


def test_watermark_reads_the_interval_end():
    assert watermark(_payloads()[0]) == NOW
    assert watermark({"seq": 1}) is None
    assert watermark({"interval": {"end": "not-a-time"}}) is None


def test_a_publish_cycle_is_audited_when_a_recorder_is_given():
    records: list[tuple[str, dict]] = []
    TelemetryPublisher([], record=lambda kind, payload: records.append((kind, payload))).publish([])
    assert records and records[0][0] == "telemetry.publish"


def test_report_serialises_for_diagnostics():
    report = PublishReport(sent=2, spooled=1, replayed=1, spool_depth=0)
    payload = report.as_dict()
    assert payload["sent"] == 2 and payload["rejected"] == 0 and payload["spool_depth"] == 0


def test_every_payload_the_publisher_forwards_was_already_valid():
    sink = FakeSink()
    TelemetryPublisher([sink]).publish(_payloads(count=2))
    assert all(validate_envelope(payload) == [] for payload in sink.payloads)
