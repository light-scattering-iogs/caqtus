from abc import ABC, abstractmethod
from enum import Enum

import attrs

from util import serialization


class TriggerEdge(Enum):
    RISING = "rising"
    FALLING = "falling"
    BOTH = "both"


serialization.register_unstructure_hook(TriggerEdge, lambda edge: edge.value)


@attrs.define
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

        Triggers with higher priority should be started before triggers with lower
        priority.
        This is used to determine the order in which the devices are started if a device
        should be triggered by another.
        """

        raise NotImplementedError


@attrs.define
class SoftwareTrigger(Trigger):
    @property
    def priority(self) -> int:
        return 0


@attrs.define
class ExternalTriggerStart(Trigger):
    edge: TriggerEdge = TriggerEdge.RISING

    @property
    def priority(self) -> int:
        return 1


@attrs.define
class ExternalClock(Trigger):
    edge: TriggerEdge = TriggerEdge.RISING

    @property
    def priority(self) -> int:
        return 1


@attrs.define
class ExternalClockOnChange(Trigger):
    edge: TriggerEdge = TriggerEdge.RISING

    @property
    def priority(self) -> int:
        return 1


serialization.include_subclasses(
    Trigger, union_strategy=serialization.include_type(tag_name="trigger_type")
)
