from typing import TypeGuard

import attrs

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


ChannelOutput = LaneValues | DeviceTrigger


def is_channel_output(obj) -> TypeGuard[ChannelOutput]:
    return isinstance(obj, (LaneValues, DeviceTrigger))
