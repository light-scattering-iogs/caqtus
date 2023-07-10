from dataclasses import dataclass
from enum import Enum, auto


class ClockStepInstruction(Enum):
    TriggerStart = auto()
    Clock = auto()


@dataclass(frozen=True)
class ClockInstruction:
    """A clock instruction is a tuple of (start, stop, frequency)"""

    start: float
    stop: float
    time_step: float
    order: ClockStepInstruction
