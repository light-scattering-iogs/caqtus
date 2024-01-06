from __future__ import annotations

from typing import TypeGuard

import attrs

from core.types.expression import Expression
from util import serialization
from ...name import DeviceName


def validate_channel_output(instance, attribute, value):
    if not is_channel_output(value):
        raise TypeError(f"Output {value} is not of type ChannelOutput")


def is_channel_output(obj) -> TypeGuard[ChannelOutput]:
    return isinstance(obj, (LaneValues, DeviceTrigger, Constant, Advance, Delay))


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


@attrs.define
class Advance:
    output: ChannelOutput = attrs.field(
        validator=validate_channel_output,
        on_setattr=attrs.setters.validate,
    )
    advance: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return f"{self.output} << {self.advance}"


@attrs.define
class Delay:
    output: ChannelOutput = attrs.field(
        validator=validate_channel_output,
        on_setattr=attrs.setters.validate,
    )
    delay: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return f"{self.delay} >> {self.output}"


ChannelOutput = LaneValues | DeviceTrigger | Constant | Advance | Delay

serialization.configure_tagged_union(ChannelOutput, "type")

Advance(advance=Expression("1"), output=LaneValues(lane="A"))
