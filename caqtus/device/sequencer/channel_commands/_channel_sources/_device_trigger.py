from __future__ import annotations

from collections.abc import Mapping
from typing import Optional, Any

import attrs
import numpy as np
from cattrs.gen import make_dict_structure_fn, override

import caqtus.formatter as fmt
from caqtus.device import DeviceName
from caqtus.device.sequencer.instructions import (
    SequencerInstruction,
    Pattern,
)
from caqtus.shot_compilation import ShotContext
from caqtus.shot_compilation.lane_compilers.timing import number_ticks, ns
from caqtus.types.recoverable_exceptions import InvalidValueError, RecoverableException
from caqtus.types.variable_name import DottedVariableName
from caqtus.utils import serialization
from ._constant import Constant
from ._trigger_compiler import TriggerCompiler
from ..channel_output import ChannelOutput, DimensionedSeries


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
        prepend: int,
        append: int,
        shot_context: ShotContext,
    ):
        target_device = self.device_name
        try:
            target_device_compiler = shot_context.get_device_compiler(target_device)
        except KeyError:
            if self.default is not None:
                evaluated_default = self.default.evaluate(
                    required_time_step,
                    prepend,
                    append,
                    shot_context,
                )
                if evaluated_default.units is not None:
                    raise InvalidValueError(
                        f"Default value for trigger for {fmt.device(target_device)} "
                        f"must be dimensionless, got "
                        f"{fmt.unit(evaluated_default.units)}"
                    )
                default_dtype = evaluated_default.values.dtype
                if default_dtype != np.bool_:
                    raise InvalidValueError(
                        f"Default value for trigger for {fmt.device(target_device)} "
                        f"must be boolean, got {default_dtype}"
                    )
                return evaluated_default
            else:
                raise InvalidValueError(
                    f"There is no {fmt.device(target_device)} to generate trigger for"
                )

        if not isinstance(target_device_compiler, TriggerCompiler):
            raise DeviceNotTriggerableError(
                f"{fmt.device(target_device)} can't be triggered"
            )

        trigger_values = target_device_compiler.compute_trigger(
            required_time_step, shot_context
        )

        # We check that the values returned by the target device compiler are valid.
        # If they are not, this a programming error, and it will cause an error further
        # down the line.
        # It means the target device compiler doesn't satisfy the trigger interface, so
        # we want to report it early.
        if not isinstance(trigger_values, SequencerInstruction):
            raise TypeError(
                f"Expected {SequencerInstruction}, got {type(trigger_values)}"
            )

        if not np.issubdtype(trigger_values.dtype, np.bool):
            raise TypeError(f"Expected boolean trigger, got {trigger_values.dtype}")

        length = number_ticks(
            0, shot_context.get_shot_duration(), required_time_step * ns
        )

        if len(trigger_values) != length:
            raise ValueError(
                f"Expected an instruction with length {length}, got "
                f"{len(trigger_values)}"
            )

        return DimensionedSeries(
            prepend * Pattern([False]) + trigger_values + append * Pattern([False]),
            units=None,
        )

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


class DeviceNotTriggerableError(RecoverableException):
    pass
