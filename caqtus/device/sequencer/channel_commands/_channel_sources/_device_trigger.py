from __future__ import annotations

from collections.abc import Mapping
from typing import Optional, Any
from typing import assert_never, TYPE_CHECKING

import attrs
import numpy as np
from cattrs.gen import make_dict_structure_fn, override

from caqtus.device import DeviceConfiguration, DeviceName
from caqtus.device.camera import CameraConfiguration
from caqtus.device.sequencer.channel_commands.channel_output import ChannelOutput
from caqtus.device.sequencer.instructions import (
    SequencerInstruction,
    Pattern,
    concatenate,
)
from caqtus.device.sequencer.trigger import ExternalClockOnChange, ExternalTriggerStart
from caqtus.device.sequencer.trigger import Trigger
from caqtus.session.shot import CameraTimeLane, TakePicture
from caqtus.shot_compilation import ShotContext
from caqtus.shot_compilation.lane_compilers.timing import number_ticks, ns
from caqtus.types.units import Unit
from caqtus.types.variable_name import DottedVariableName
from caqtus.utils import serialization
from ._adaptative_clock import get_adaptive_clock
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

    def evaluate(
        self,
        required_time_step: int,
        required_unit: Optional[Unit],
        prepend: int,
        append: int,
        shot_context: ShotContext,
    ) -> SequencerInstruction:
        device = self.device_name
        try:
            device_config = shot_context.get_device_config(device)
        except KeyError:
            if self.default is not None:
                return self.default.evaluate(
                    required_time_step,
                    required_unit,
                    prepend,
                    append,
                    shot_context,
                )
            else:
                raise ValueError(
                    f"Could not find device <{device}> when evaluating output "
                    f"<{self}>"
                )
        if required_unit is not None:
            raise ValueError(
                f"Cannot evaluate trigger for device <{device}> with unit "
                f"{required_unit:~}"
            )
        trigger_values = evaluate_device_trigger(
            device, device_config, required_time_step, shot_context
        )
        return prepend * Pattern([False]) + trigger_values + append * Pattern([False])

    def evaluate_max_advance_and_delay(
        self,
        time_step: int,
        variables: Mapping[DottedVariableName, Any],
    ) -> tuple[int, int]:
        return 0, 0


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


if TYPE_CHECKING:
    from ...configuration import SequencerConfiguration


def evaluate_device_trigger(
    device: DeviceName,
    device_config: DeviceConfiguration,
    time_step: int,
    shot_context: ShotContext,
) -> SequencerInstruction[np.bool_]:
    """Computes the trigger for a device.

    If the target device is a sequencer, this function will compute the trigger
    depending on the target sequencer's trigger configuration.
    If the target device is a camera, this function will compute a trigger that is
    high when a picture is being taken and low otherwise.
    If the target device is neither a sequencer nor a camera, this function will
    output a trigger that is high for half the shot duration and low for the other
    half.
    """

    from ...configuration import SequencerConfiguration

    if isinstance(device_config, SequencerConfiguration):
        slave_parameters = shot_context.get_shot_parameters(device)
        slave_instruction = slave_parameters["sequence"]
        return evaluate_trigger_for_sequencer(
            slave=device,
            slave_instruction=slave_instruction,
            slave_trigger=device_config.trigger,
            slave_time_step=device_config.time_step,
            master_time_step=time_step,
            length=number_ticks(0, shot_context.get_shot_duration(), time_step * ns),
        )
    elif isinstance(device_config, CameraConfiguration):
        return evaluate_trigger_for_camera(device, time_step, shot_context)
    else:
        length = number_ticks(0, shot_context.get_shot_duration(), time_step * ns)
        high_duration = length // 2
        low_duration = length - high_duration
        if high_duration == 0 or low_duration == 0:
            raise ValueError(
                "The shot duration is too short to generate a trigger pulse for "
                f"device '{device}'"
            )
        return Pattern([True]) * high_duration + Pattern([False]) * low_duration


def evaluate_trigger_for_sequencer(
    slave: DeviceName,
    slave_instruction: SequencerInstruction,
    slave_trigger: Trigger,
    slave_time_step: int,
    master_time_step: int,
    length: int,
) -> SequencerInstruction[np.bool_]:
    if isinstance(slave_trigger, ExternalClockOnChange):
        single_clock_pulse = get_master_clock_pulse(slave_time_step, master_time_step)
        instruction = get_adaptive_clock(slave_instruction, single_clock_pulse)[:length]
        return instruction
    elif isinstance(slave_trigger, ExternalTriggerStart):
        high_duration = length // 2
        low_duration = length - high_duration
        if high_duration == 0 or low_duration == 0:
            raise ValueError(
                "The shot duration is too short to generate a trigger pulse for "
                f"sequencer '{slave}'"
            )
        return Pattern([True]) * high_duration + Pattern([False]) * low_duration
    else:
        raise NotImplementedError(
            f"Cannot evaluate trigger for trigger of type " f"{type(slave_trigger)}"
        )


def evaluate_trigger_for_camera(
    device: DeviceName, time_step: int, shot_context: ShotContext
) -> SequencerInstruction[np.bool_]:
    try:
        lane = shot_context.get_lane(device)
    except KeyError:
        # If there is no lane with the name of this camera, it probably means that
        # the camera is not used in this shot, so instead of raising an error, we
        # just return no trigger, but I don't know if it is the best option.
        # Probably better to fall back to the default channel function.
        length = number_ticks(0, shot_context.get_shot_duration(), time_step * ns)
        return Pattern([False]) * length
    if not isinstance(lane, CameraTimeLane):
        raise ValueError(
            f"Asked to generate trigger for device '{device}', which is a "
            f"camera, but the lane with this name is not a camera lane "
            f"(got {type(lane)})"
        )
    return compile_camera_trigger(lane, time_step, shot_context)


def compile_camera_trigger(
    lane: CameraTimeLane, time_step: int, shot_context: ShotContext
) -> SequencerInstruction[np.bool_]:
    step_bounds = shot_context.get_step_bounds()

    instructions: list[SequencerInstruction[np.bool_]] = []
    for value, (start, stop) in zip(lane.block_values(), lane.block_bounds()):
        length = number_ticks(step_bounds[start], step_bounds[stop], time_step * ns)
        if isinstance(value, TakePicture):
            if length == 0:
                raise ValueError(
                    f"No trigger can be generated for picture "
                    f"'{value.picture_name}' because its exposure is too short"
                    f"({(step_bounds[stop] - step_bounds[start])*1e9} ns) with "
                    f"respect to the time step ({time_step} ns)"
                )
            instructions.append(Pattern([True]) * length)
        elif value is None:
            instructions.append(Pattern([False]) * length)
        else:
            assert_never(value)
    return concatenate(*instructions)


def get_master_clock_pulse(
    slave_time_step: int, master_time_step: int
) -> SequencerInstruction[np.bool_]:
    _, high, low = high_low_clicks(slave_time_step, master_time_step)
    single_clock_pulse = Pattern([True]) * high + Pattern([False]) * low
    assert len(single_clock_pulse) * master_time_step == slave_time_step
    return single_clock_pulse


def high_low_clicks(slave_time_step: int, master_timestep: int) -> tuple[int, int, int]:
    """Return the number of steps the master sequencer must be high then low to
    produce a clock pulse for the slave sequencer.

    Returns:
        A tuple with its first element being the number of master steps that constitute
        a full slave clock cycle, the second element being the number of master steps
        for which the master must be high and the third element being the number of
        master steps for which the master must be low.
        The first element is the sum of the second and third elements.
    """

    if not slave_time_step >= 2 * master_timestep:
        raise ValueError(
            "Slave time step must be at least twice the master sequencer time step"
        )
    div, mod = divmod(slave_time_step, master_timestep)
    if not mod == 0:
        raise ValueError(
            "Slave time step must be an integer multiple of the master sequencer time "
            "step"
        )
    if div % 2 == 0:
        return div, div // 2, div // 2
    else:
        return div, div // 2 + 1, div // 2
