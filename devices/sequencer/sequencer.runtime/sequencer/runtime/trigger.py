from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto


class TriggerEdge(Enum):
    RISING = auto()
    FALLING = auto()
    BOTH = auto()


class Trigger(ABC):
    def is_software_trigger(self) -> bool:
        return isinstance(self, SoftwareTrigger)

    def is_external_trigger_start(self) -> bool:
        return isinstance(self, ExternalTriggerStart)

    def is_external_clock(self) -> bool:
        return isinstance(self, ExternalClock)

    @property
    @abstractmethod
    def priority(self) -> int:
        """The priority of the trigger.

        Triggers with higher priority should be started before triggers with lower priority. This is used to determine
        the order in which the devices are started if a device should be triggered by another.
        """
        raise NotImplementedError


class SoftwareTrigger(Trigger):
    @property
    def priority(self) -> int:
        return 0


@dataclass(frozen=True)
class ExternalTriggerStart(Trigger):
    edge: TriggerEdge = TriggerEdge.RISING

    @property
    def priority(self) -> int:
        return 1


@dataclass(frozen=True)
class ExternalClock(Trigger):
    edge: TriggerEdge = TriggerEdge.RISING

    @property
    def priority(self) -> int:
        return 1


@dataclass(frozen=True)
class ExternalClockOnChange(Trigger):
    edge: TriggerEdge = TriggerEdge.RISING

    @property
    def priority(self) -> int:
        return 1
