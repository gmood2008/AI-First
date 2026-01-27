"""
Domain A: Signal Ingestion API (事实层)

只记录事实，不判断、不聚合、不删除。
采用 Event Sourcing / Append-only 模式。
"""

from .models import Signal, SignalType, SignalSeverity, SignalSource
from .signal_bus import SignalBus
from .repository import SignalRepository

__all__ = [
    "Signal",
    "SignalType",
    "SignalSeverity",
    "SignalSource",
    "SignalBus",
    "SignalRepository",
]
