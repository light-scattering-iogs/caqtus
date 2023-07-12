from dataclasses import dataclass
from enum import Enum, auto


@dataclass(frozen=True)
class ClockInstruction:
    """A clock instruction is a tuple of (start, stop, frequency)"""

    start: float
    stop: float
    time_step: int
    order: "StepInstruction"

    class StepInstruction(Enum):
        TriggerStart = auto()
        Clock = auto()
