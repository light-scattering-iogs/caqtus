from enum import Enum
from typing import TypeAlias, TypeGuard

import attrs


class TriggerEdge(Enum):
    RISING = "rising"
    FALLING = "falling"
    BOTH = "both"

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}"


@attrs.define
class SoftwareTrigger:
    pass


@attrs.define
class ExternalTriggerStart:
    edge: TriggerEdge = TriggerEdge.RISING


@attrs.define
class ExternalClock:
    edge: TriggerEdge = TriggerEdge.RISING


@attrs.define
class ExternalClockOnChange:
    edge: TriggerEdge = TriggerEdge.RISING


Trigger: TypeAlias = (
    SoftwareTrigger | ExternalTriggerStart | ExternalClock | ExternalClockOnChange
)


def is_trigger(value) -> TypeGuard[Trigger]:
    return isinstance(
        value,
        (SoftwareTrigger, ExternalTriggerStart, ExternalClock, ExternalClockOnChange),
    )
