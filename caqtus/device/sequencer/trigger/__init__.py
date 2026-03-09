"""Defines what kind of triggers can be used for a sequencer."""

from ._trigger import (
    Trigger,
    SoftwareTrigger,
    ExternalTriggerStart,
    ExternalClock,
    ExternalClockOnChange,
    TriggerEdge,
    is_trigger,
)

__all__ = [
    "Trigger",
    "SoftwareTrigger",
    "ExternalClock",
    "ExternalTriggerStart",
    "ExternalClockOnChange",
    "TriggerEdge",
    "is_trigger",
]
