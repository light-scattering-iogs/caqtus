from typing import TypeGuard

import attrs

from core.types.expression import Expression
from ...name import DeviceName


@attrs.define
class LaneValues:
    lane: str = attrs.field(
        converter=str,
        on_setattr=attrs.setters.convert,
    )

    def __str__(self):
        return self.lane


@attrs.define
class DeviceTrigger:
    device_name: DeviceName = attrs.field(
        converter=lambda x: DeviceName(str(x)),
        on_setattr=attrs.setters.convert,
    )

    def __str__(self):
        return f"trig({self.device_name})"


@attrs.define
class Constant:
    value: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return str(self.value)


ChannelOutput = LaneValues | DeviceTrigger | Constant


def is_channel_output(obj) -> TypeGuard[ChannelOutput]:
    return isinstance(obj, (LaneValues, DeviceTrigger, Constant))
