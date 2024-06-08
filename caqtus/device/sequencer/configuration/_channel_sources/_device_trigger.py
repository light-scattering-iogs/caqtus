from __future__ import annotations

from typing import Optional

import attrs

from caqtus.device.name import DeviceName
from caqtus.device.sequencer.configuration.channel_output import ChannelOutput
from caqtus.utils import serialization


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


def unstructure_device_trigger(device_trigger: DeviceTrigger):
    return {
        "device_name": device_trigger.device_name,
        "default": serialization.unstructure(
            device_trigger.default, Optional[ChannelOutput]
        ),
    }


serialization.register_unstructure_hook(DeviceTrigger, unstructure_device_trigger)
