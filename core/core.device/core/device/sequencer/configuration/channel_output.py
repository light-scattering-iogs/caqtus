from typing import TypeGuard

import attrs

from ...name import DeviceName


@attrs.define
class LaneValues:
    lane: str = attrs.field(
        converter=str,
        validator=attrs.validators.instance_of(str),
    )

    def __str__(self):
        return self.lane


@attrs.define
class DeviceTrigger:
    device_name: DeviceName = attrs.field(
        converter=str,
        validator=attrs.validators.instance_of(str),
    )

    def __str__(self):
        return f"trig({self.device_name})"


ChannelOutput = LaneValues | DeviceTrigger


def is_channel_output(obj) -> TypeGuard[ChannelOutput]:
    return isinstance(obj, (LaneValues, DeviceTrigger))
