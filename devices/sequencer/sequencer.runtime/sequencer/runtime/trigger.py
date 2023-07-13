from abc import ABC
from dataclasses import dataclass
from enum import Enum, auto


class TriggerEdge(Enum):
    RISING = auto()
    FALLING = auto()
    BOTH = auto()


class Trigger(ABC):
    def is_software_trigger(self) -> bool:
        return isinstance(self, SoftwareTrigger)


class SoftwareTrigger(Trigger):
    pass


@dataclass(frozen=True)
class ExternalTriggerStart(Trigger):
    edge: TriggerEdge = TriggerEdge.RISING


@dataclass(frozen=True)
class ExternalClock(Trigger):
    edge: TriggerEdge = TriggerEdge.RISING


@dataclass(frozen=True)
class ExternalClockOnChange(Trigger):
    edge: TriggerEdge = TriggerEdge.RISING
