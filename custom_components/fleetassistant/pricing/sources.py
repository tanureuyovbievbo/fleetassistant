"""Tariff sources and the merge between them (ADR-0019).

Two sources answer the same question — "what does a kWh cost, period by period":

* a **user** source (flat rate, TOU block schedule, or a pasted series) entered by
  an installer or homeowner, and
* a **cloud** source (a vendor feed or an existing HA integration) that quotes
  prices with an expiry.

HAEO only ever sees the merged series, so which source won a period is a
provenance fact, not a modelling choice. Provenance travels in the sensor's
attributes and in telemetry; it never contaminates the value the optimizer reads.

Staleness is not an error. A lapsed cloud quote falls back to the user schedule
and marks those periods degraded, because a plan built on a plausible old price is
better than a plan built on ``unknown`` — as long as we say which it was.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .providers import RateProvider
from .series import Point, build_series

#: How a period's price came to exist.
QUALITIES = ("quoted", "entered", "fallback", "stale")

#: Who wins when both sources have a price for the same period (ADR-0019).
AUTHORITIES = ("cloud", "user", "user_unless_stale")

#: Default authority per deployment profile: a cloud-primary site has no
#: installer on site to type a tariff, a gateway site's operator knows the rate.
DEFAULT_AUTHORITY = {"cloud_primary": "cloud", "gateway_primary": "user"}

#: A cloud fetch is ``(start, end) -> [(timestamp, currency_per_kwh), ...]``.
Fetcher = Callable[[datetime, datetime], Awaitable[Sequence[tuple[datetime, float]]]]


@dataclass(frozen=True)
class QuotedPoint:
    """One period's price with the source that supplied it."""

    ts: datetime
    value: float | None
    source: str = ""
    quality: str = "quoted"


@dataclass(frozen=True)
class SeriesResult:
    """What one source says over a window, plus how fresh the answer is."""

    source: str
    quality: str
    points: tuple[QuotedPoint, ...]
    fetched_at: datetime | None = None
    expires_at: datetime | None = None
    warnings: tuple[str, ...] = ()

    def value_at(self, ts: datetime) -> float | None:
        for point in self.points:
            if point.ts == ts:
                return point.value
        return None

    def is_fresh(self, now: datetime | None = None) -> bool:
        """A source without an expiry (an entered schedule) is always fresh."""
        if self.expires_at is None or now is None:
            return True
        return now < self.expires_at


def series_from_provider(
    provider: RateProvider,
    *,
    start: datetime,
    end: datetime,
    step_minutes: int,
    quality: str = "entered",
    fetched_at: datetime | None = None,
    expires_at: datetime | None = None,
    warnings: Sequence[str] = (),
) -> SeriesResult:
    """Sample a rate provider into a :class:`SeriesResult`."""
    points = build_series(start, (end - start).total_seconds() / 3600.0, step_minutes, provider.price_at)
    quoted = tuple(
        QuotedPoint(ts=point.ts, value=point.value, source=provider.name, quality=quality) for point in points
    )
    return SeriesResult(
        source=provider.name,
        quality=quality,
        points=quoted,
        fetched_at=fetched_at,
        expires_at=expires_at,
        warnings=tuple(warnings),
    )


@dataclass
class CloudTariffSource:
    """A quoted feed with a TTL, an injected fetcher, and a request counter.

    The fetcher is injected rather than imported so the whole cloud path is
    testable without a network, and so a vendor adapter (Tesla Fleet, SolarEdge
    Open, Tibber, …) stays behind the adapter layer instead of leaking into
    pricing. ``requests`` exists for the quota math C-22 demands before a cadence
    is promised.
    """

    name: str
    fetcher: Fetcher | None = None
    ttl: timedelta = timedelta(hours=6)
    cache: SeriesResult | None = None
    requests: int = 0

    async def async_resolve(
        self,
        *,
        start: datetime,
        end: datetime,
        step_minutes: int = 60,
        now: datetime | None = None,
    ) -> SeriesResult | None:
        """Return fresh quotes, refreshing through the fetcher when needed."""
        if self.fetcher is None:
            return self.stale_view(now)
        if self.cache is not None and self.cache.is_fresh(now):
            return self.cache
        rows = await self.fetcher(start, end)
        self.requests += 1
        fetched = now
        points = tuple(
            QuotedPoint(ts=ts, value=float(value), source=self.name, quality="quoted")
            for ts, value in sorted(rows)
        )
        self.cache = SeriesResult(
            source=self.name,
            quality="quoted",
            points=points,
            fetched_at=fetched,
            expires_at=(fetched + self.ttl) if fetched is not None else None,
        )
        return self.cache

    def stale_view(self, now: datetime | None = None) -> SeriesResult | None:
        """Last known quotes, marked ``stale`` when their TTL has lapsed."""
        if self.cache is None:
            return None
        if self.cache.is_fresh(now):
            return self.cache
        return SeriesResult(
            source=self.cache.source,
            quality="stale",
            points=tuple(
                QuotedPoint(ts=point.ts, value=point.value, source=point.source, quality="stale")
                for point in self.cache.points
            ),
            fetched_at=self.cache.fetched_at,
            expires_at=self.cache.expires_at,
            warnings=self.cache.warnings,
        )


@dataclass(frozen=True)
class Divergence:
    """Both sources priced a period and they disagreed."""

    ts: datetime
    cloud: float
    user: float
    chosen: float
    source: str

    @property
    def delta(self) -> float:
        return abs(self.cloud - self.user)


@dataclass(frozen=True)
class MergedPoint:
    ts: datetime
    value: float
    source: str
    quality: str

    @property
    def degraded(self) -> bool:
        return self.quality == "stale"


@dataclass
class MergedTariff:
    """The series HAEO reads, with the provenance behind every period."""

    site_id: str
    authority: str
    points: tuple[MergedPoint, ...] = ()
    divergences: tuple[Divergence, ...] = ()
    fallbacks: tuple[datetime, ...] = ()
    stale: tuple[datetime, ...] = ()
    missing: tuple[datetime, ...] = ()
    warnings: tuple[str, ...] = ()
    sources: dict[str, int] = field(default_factory=dict)

    def as_series(self) -> list[Point]:
        """Plain points for the compiler — provenance stays out of the value."""
        return [Point(ts=point.ts, value=point.value) for point in self.points]

    def value_at(self, ts: datetime) -> float | None:
        for point in self.points:
            if point.ts == ts:
                return point.value
        return None

    @property
    def degraded_share(self) -> float:
        if not self.points:
            return 1.0
        return len(self.stale) / len(self.points)

    @property
    def provenance(self) -> dict[str, int]:
        return dict(self.sources)


def merge_tariffs(
    *,
    site_id: str,
    cloud: SeriesResult | None = None,
    user: SeriesResult | None = None,
    authority: str = "user",
    now: datetime | None = None,
    tolerance: float = 0.005,
) -> MergedTariff:
    """Merge a cloud quote and a user schedule under an explicit authority.

    ``authority`` decides the *primary* source; the other one fills periods the
    primary cannot price. A stale primary loses to a fresh secondary, and the
    period is recorded as a fallback.
    """
    if authority not in AUTHORITIES:
        raise ValueError(f"unknown price authority {authority!r}; expected one of {AUTHORITIES}")

    sources = {"cloud": cloud, "user": user}
    primary, secondary = ("cloud", "user") if authority.startswith("cloud") else ("user", "cloud")
    order = [name for name in (primary, secondary) if sources[name] is not None]

    timestamps: set[datetime] = set()
    for result in sources.values():
        if result is not None:
            timestamps.update(point.ts for point in result.points)

    points: list[MergedPoint] = []
    fallbacks: list[datetime] = []
    stale: list[datetime] = []
    missing: list[datetime] = []
    divergences: list[Divergence] = []
    warnings: list[str] = []

    # A source that knows something about itself (a fallback export value, an
    # expired vendor token) says so; the merged series must not swallow it.
    for result in sources.values():
        if result is not None:
            warnings.extend(f"{result.source}: {warning}" for warning in result.warnings)

    for ts in sorted(timestamps):
        candidates: list[tuple[str, float, SeriesResult, bool]] = []
        for role in order:
            result = sources[role]
            assert result is not None  # narrowed by `order`
            value = result.value_at(ts)
            if value is None:
                continue
            candidates.append((role, value, result, not result.is_fresh(now)))

        if not candidates:
            missing.append(ts)
            continue

        fresh = [candidate for candidate in candidates if not candidate[3]]
        role, value, result, is_stale = (fresh or candidates)[0]
        quality = "stale" if is_stale else result.quality

        if is_stale:
            stale.append(ts)
        if role != primary:
            fallbacks.append(ts)
        points.append(MergedPoint(ts=ts, value=value, source=result.source, quality=quality))

        cloud_value = cloud.value_at(ts) if cloud is not None else None
        user_value = user.value_at(ts) if user is not None else None
        if cloud_value is not None and user_value is not None and abs(cloud_value - user_value) > tolerance:
            divergences.append(
                Divergence(ts=ts, cloud=cloud_value, user=user_value, chosen=value, source=result.source)
            )

    counts: dict[str, int] = {}
    for point in points:
        counts[point.source] = counts.get(point.source, 0) + 1

    if not points:
        warnings.append(
            "no tariff source produced a price: HAEO would plan against unknown prices (C-23)"
        )
    if authority == "cloud" and cloud is None:
        warnings.append(
            "authority is 'cloud' but no cloud tariff is configured; the user schedule is in use"
        )
    if stale:
        warnings.append(
            f"{len(stale)} periods carry a stale cloud quote (TTL lapsed): refresh it, or "
            "lower the promised cadence (C-22)"
        )
    if fallbacks and not stale:
        warnings.append(
            f"{len(fallbacks)} periods fell back from the {primary} source to {secondary}"
        )
    if divergences:
        worst = max(divergences, key=lambda item: item.delta)
        warnings.append(
            f"cloud and user tariffs disagree in {len(divergences)} periods "
            f"(max {worst.delta:.3f} at {worst.ts.isoformat()}); authority {authority!r} applied"
        )
    if missing:
        warnings.append(f"{len(missing)} periods have no price from any source")

    return MergedTariff(
        site_id=site_id,
        authority=authority,
        points=tuple(points),
        divergences=tuple(divergences),
        fallbacks=tuple(fallbacks),
        stale=tuple(stale),
        missing=tuple(missing),
        warnings=tuple(warnings),
        sources=counts,
    )
