from __future__ import annotations

from typing import Optional

import attrs
from cattrs.gen import make_dict_structure_fn, override

from caqtus.device.name import DeviceName
from caqtus.device.sequencer.configuration.channel_output import ChannelOutput
from caqtus.utils import serialization
from ._constant import Constant


@attrs.define
class DeviceTrigger(ChannelOutput):
    """Indicates that the output should be a trigger for a given device.

    Fields:
        device_name: The name of the device to generate a trigger for.
        default: If the device is not used in the sequence, fallback to this.
    """

    device_name: DeviceName = attrs.field(
        converter=lambda x: DeviceName(str(x)),
        on_setattr=attrs.setters.convert,
    )
    default: Optional[ChannelOutput] = attrs.field(
        default=None,
        validator=attrs.validators.optional(
            attrs.validators.instance_of(ChannelOutput)
        ),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return f"trig({self.device_name})"


def structure_default(data, _):
    # We need this custom structure hook, because in the past the default value of a
    # DeviceTrigger was a Constant and not any ChannelOutput.
    # In that case, the type of the default value was not serialized, so we need to
    # deal with this special case.
    if data is None:
        return None
    if "type" in data:
        return serialization.structure(data, ChannelOutput)
    else:
        return serialization.structure(data, Constant)


structure_device_trigger = make_dict_structure_fn(
    DeviceTrigger,
    serialization.converters["json"],
    default=override(struct_hook=structure_default),
)


serialization.register_structure_hook(DeviceTrigger, structure_device_trigger)
