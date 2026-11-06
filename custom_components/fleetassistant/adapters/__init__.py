"""Control adapter package (C-09).

Only modules inside this package may perform device I/O. The boundary is
enforced by tools/check_boundaries.py in CI.
"""

from .base import AdapterError, Capability, Command, ControlAdapter, WriteResult
from .safety import SafetyPipeline, TokenBucket
from .stubs import ApiStubAdapter, ModbusStubAdapter

__all__ = [
    "AdapterError",
    "ApiStubAdapter",
    "Capability",
    "Command",
    "ControlAdapter",
    "ModbusStubAdapter",
    "SafetyPipeline",
    "TokenBucket",
    "WriteResult",
]
