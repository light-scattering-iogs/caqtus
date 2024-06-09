from __future__ import annotations

import attrs
import cattrs

from caqtus.types.expression import Expression
from caqtus.utils import serialization
from .channel_output import ChannelOutput


@attrs.define
class Advance(ChannelOutput):
    input_: ChannelOutput = attrs.field(
        validator=attrs.validators.instance_of(ChannelOutput),
        on_setattr=attrs.setters.validate,
    )
    advance: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return f"{self.input_} << {self.advance}"


# Workaround for https://github.com/python-attrs/cattrs/issues/430
advance_structure_hook = cattrs.gen.make_dict_structure_fn(
    Advance,
    serialization.converters["json"],
    input_=cattrs.override(
        struct_hook=lambda x, _: serialization.structure(x, ChannelOutput)
    ),
)

serialization.register_structure_hook(Advance, advance_structure_hook)


@attrs.define
class Delay(ChannelOutput):
    input_: ChannelOutput = attrs.field(
        validator=attrs.validators.instance_of(ChannelOutput),
        on_setattr=attrs.setters.validate,
    )
    delay: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return f"{self.delay} >> {self.input_}"


# Workaround for https://github.com/python-attrs/cattrs/issues/430
delay_structure_hook = cattrs.gen.make_dict_structure_fn(
    Delay,
    serialization.converters["json"],
    input_=cattrs.override(
        struct_hook=lambda x, _: serialization.structure(x, ChannelOutput)
    ),
)

serialization.register_structure_hook(Delay, delay_structure_hook)


@attrs.define
class BroadenLeft(ChannelOutput):
    """Indicates that output should go high before the input pulses go high.

    The output y(t) of this operation should be high when any of the input x(s) is high
    for s in [t, t + width].

    The operation is only valid for boolean inputs, and it will produce a boolean
    output.

    It is meant to be used to compensate for finite rise times in the hardware.
    For example, if a shutter takes 10 ms to open, and we want to open it at time t, we
    can use this operation to start opening the shutter at time t - 10 ms.
    """

    input_: ChannelOutput = attrs.field(
        validator=attrs.validators.instance_of(ChannelOutput),
        on_setattr=attrs.setters.validate,
    )
    width: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )


broaden_left_structure_hook = cattrs.gen.make_dict_structure_fn(
    BroadenLeft,
    serialization.converters["json"],
    input_=cattrs.override(
        struct_hook=lambda x, _: serialization.structure(x, ChannelOutput)
    ),
)

serialization.register_structure_hook(BroadenLeft, broaden_left_structure_hook)
