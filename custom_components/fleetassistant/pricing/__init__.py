"""Generic price and target model (C-13, C-14).

Ship-with-v1: flat, TOU block schedules, dynamic feeds, target overlays, and a
priced degradation term. Regional rate packs and event programs are installable
rule packs, never core code.
"""

from .compiler import PriceInputs, compile_price_inputs
from .overlay import TargetOverlay, apply_overlays, overlay_windows
from .providers import (
    DynamicSeries,
    ExportValueCurve,
    FlatRate,
    PriceProviderError,
    RateProvider,
    TouBlock,
    TouSchedule,
    provider_from_profile,
)
from .series import FORECAST_FORMAT_VERIFIED, Point, build_series, resample_hold, to_forecast

__all__ = [
    "DynamicSeries",
    "ExportValueCurve",
    "FORECAST_FORMAT_VERIFIED",
    "FlatRate",
    "Point",
    "PriceInputs",
    "PriceProviderError",
    "RateProvider",
    "TargetOverlay",
    "TouBlock",
    "TouSchedule",
    "apply_overlays",
    "build_series",
    "compile_price_inputs",
    "overlay_windows",
    "provider_from_profile",
    "resample_hold",
    "to_forecast",
]
