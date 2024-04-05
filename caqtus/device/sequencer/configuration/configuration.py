import functools
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Type, ClassVar, TypeVar, Generic, TypedDict, Any, Optional

import attrs
import numpy as np

from caqtus.session.shot import DigitalTimeLane, AnalogTimeLane
from caqtus.shot_compilation import (
    SequenceContext,
    ShotContext,
    compile_analog_lane,
    compile_digital_lane,
)
from caqtus.shot_compilation.lane_compilers.timing import number_ticks, ns
from caqtus.types.expression import Expression
from caqtus.types.parameter import magnitude_in_unit
from caqtus.types.units import Unit
from caqtus.types.variable_name import DottedVariableName
from caqtus.utils import add_exc_note
from ._generate_device_trigger import evaluate_device_trigger
from .channel_output import (
    ChannelOutput,
    is_channel_output,
    is_value_source,
    TimeIndependentMapping,
    Advance,
    Delay,
    Constant,
    LaneValues,
    CalibratedAnalogMapping,
    DeviceTrigger,
)
from .trigger import Trigger, is_trigger
from ..instructions import SequencerInstruction, with_name, stack_instructions, Pattern
from ..runtime import Sequencer
from ... import DeviceName
from ...configuration import DeviceConfiguration


def validate_channel_output(instance, attribute, value):
    if not is_channel_output(value):
        raise TypeError(f"Output {value} is not of type ChannelOutput")


@attrs.define
class ChannelConfiguration(ABC):
    """Contains information to computer the output of a channel."""

    description: str = attrs.field(
        converter=str,
        on_setattr=attrs.setters.convert,
    )
    output: ChannelOutput = attrs.field(
        validator=validate_channel_output,
        on_setattr=attrs.setters.validate,
    )


@attrs.define
class DigitalChannelConfiguration(ChannelConfiguration):
    def __str__(self):
        return f"digital channel '{self.description}'"


@attrs.define
class AnalogChannelConfiguration(ChannelConfiguration):
    output_unit: str = attrs.field(
        converter=str,
        on_setattr=attrs.setters.convert,
    )

    def __str__(self):
        return f"analog channel '{self.description}' with unit {self.output_unit}"


def validate_trigger(instance, attribute, value):
    if not is_trigger(value):
        raise TypeError(f"Trigger {value} is not of type Trigger")


SequencerType = TypeVar("SequencerType", bound=Sequencer)


class SequencerInitParams(TypedDict):
    trigger: Trigger


class SequencerUpdateParams(TypedDict):
    sequence: SequencerInstruction


@attrs.define
class SequencerConfiguration(
    DeviceConfiguration[SequencerType], ABC, Generic[SequencerType]
):
    """Holds the static configuration of a sequencer device.

    Fields:
        number_channels: The number of channels of the device.
        time_step: The quantization time step used, in nanoseconds. The device can only
            update its output at multiples of this time step.
        channels: The configuration of the channels of the device. The length of this
            list must match the number of channels of the device.
    """

    number_channels: ClassVar[int]
    time_step: int = attrs.field(
        converter=int,
        validator=attrs.validators.ge(1),
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )
    channels: tuple[ChannelConfiguration, ...] = attrs.field(
        converter=tuple,
        validator=attrs.validators.deep_iterable(
            member_validator=attrs.validators.instance_of(ChannelConfiguration)
        ),
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )
    trigger: Trigger = attrs.field(validator=validate_trigger)

    @classmethod
    @abstractmethod
    def channel_types(cls) -> tuple[Type[ChannelConfiguration], ...]: ...

    @channels.validator  # type: ignore
    def validate_channels(self, _, channels):
        if len(channels) != self.number_channels:
            raise ValueError(
                f"The length of channels ({len(channels)}) doesn't match the number of"
                f" channels {self.number_channels}"
            )
        for channel, channel_type in zip(channels, self.channel_types(), strict=True):
            if not isinstance(channel, channel_type):
                raise TypeError(
                    f"Channel {channel} is not of the expected type {channel_type}"
                )

    def __getitem__(self, item):
        return self.channels[item]

    def get_device_init_args(
        self, device_name: DeviceName, sequence_context: SequenceContext
    ) -> SequencerInitParams:
        # TODO: raise DeviceNotUsedException if the sequencer is not used for the
        #  current sequence
        return {"trigger": self.trigger}

    def compile_device_shot_parameters(
        self,
        device_name: DeviceName,
        shot_context: ShotContext,
    ) -> SequencerUpdateParams:
        channel_instructions = []
        for channel_number, channel in enumerate(self.channels):
            if isinstance(channel, AnalogChannelConfiguration):
                required_unit = Unit(channel.output_unit)
            else:
                required_unit = None
            try:
                max_advance, max_delay = self._find_max_advance_and_delays(
                    shot_context.get_variables()
                )
                output_values = evaluate_output(
                    channel.output,
                    self.time_step,
                    required_unit,
                    max_advance,
                    max_delay,
                    shot_context,
                )
            except Exception as e:
                raise SequencerCompilationError(
                    f"Error occurred when evaluating output for channel "
                    f"{channel_number} ({channel}) of sequencer "
                    f"{self}"
                ) from e
            instruction = _convert_channel_instruction(output_values, channel)
            channel_instructions.append(with_name(instruction, f"ch {channel_number}"))
        stacked = stack_instructions(channel_instructions)
        return {"sequence": stacked}

    def _find_max_advance_and_delays(
        self, variables: Mapping[DottedVariableName, Any]
    ) -> tuple[int, int]:
        advances_and_delays = [
            _evaluate_max_advance_and_delay(channel.output, self.time_step, variables)
            for channel in self.channels
        ]
        advances, delays = zip(*advances_and_delays)
        return max(advances), max(delays)


@functools.singledispatch
def evaluate_output(
    output_: ChannelOutput,
    required_time_step: int,
    required_unit: Optional[Unit],
    prepend: int,
    append: int,
    shot_context: ShotContext,
) -> SequencerInstruction:
    """Evaluate the output of a channel with the required parameters.

    Args:
        output_: The output to evaluate.
        required_time_step: The time step of the sequencer that will use the
        output, in ns.
        required_unit: The unit in which the output should be expressed when
        evaluated.
        prepend: The number of time steps to add at the beginning of the output.
        append: The number of time steps to add at the end of the output.
        shot_context: The context of the shot in which the output is evaluated.
    """

    raise NotImplementedError(f"Cannot evaluate output <{output_}>")


@evaluate_output.register
def _(
    output_: Constant,
    required_time_step: int,
    required_unit: Optional[Unit],
    prepend: int,
    append: int,
    shot_context: ShotContext,
) -> SequencerInstruction:
    """Evaluate a constant output.

    Returns an instruction that has constant values for the entire shot duration.
    The constant value is obtained by evaluating the value stored in the constant
    output within the shot namespace.
    Note that `constant` refers to a value constant in shot time, not necessarily
    constant across shots.
    """

    length = (
        number_ticks(0, shot_context.get_shot_duration(), required_time_step * ns)
        + prepend
        + append
    )
    expression = output_.value
    value = expression.evaluate(shot_context.get_variables())
    magnitude = magnitude_in_unit(value, required_unit)
    return Pattern([magnitude]) * length


@evaluate_output.register
def _(
    output_: LaneValues,
    required_time_step: int,
    required_unit: Optional[Unit],
    prepend: int,
    append: int,
    shot_context: ShotContext,
) -> SequencerInstruction:
    """Evaluate the output of a channel as the values of a lane.

    This function will look in the shot time lanes to find the lane referenced by
    the output and evaluate the values of this lane.
    If the lane cannot be found, and the output has a default value, this default
    value will be used.
    If the lane cannot be found and there is no default value, a ValueError will be
    raised.
    """

    lane_name = output_.lane
    try:
        lane = shot_context.get_lane(lane_name)
    except KeyError:
        if output_.default is not None:
            constant = Constant(output_.default)
            return evaluate_output(
                constant,
                required_time_step,
                required_unit,
                prepend,
                append,
                shot_context,
            )
        else:
            raise ValueError(
                f"Could not find lane <{lane_name}> when evaluating output "
                f"<{output_}>"
            )
    if isinstance(lane, DigitalTimeLane):
        if required_unit is not None:
            raise ValueError(
                f"Cannot evaluate digital lane <{lane_name}> with unit "
                f"{required_unit:~}"
            )
        with add_exc_note(f"When evaluating digital lane <{lane_name}>"):
            lane_values = compile_digital_lane(lane, required_time_step, shot_context)
    elif isinstance(lane, AnalogTimeLane):
        with add_exc_note(f"When evaluating analog lane <{lane_name}>"):
            lane_values = compile_analog_lane(
                lane, required_unit, required_time_step, shot_context
            )
    else:
        raise TypeError(f"Cannot evaluate values of lane with type {type(lane)}")
    prepend_pattern = prepend * Pattern([lane_values[0]])
    append_pattern = append * Pattern([lane_values[-1]])
    return prepend_pattern + lane_values + append_pattern


@evaluate_output.register
def _(
    mapping: CalibratedAnalogMapping,
    required_time_step: int,
    required_unit: Optional[Unit],
    prepend: int,
    append: int,
    shot_context: ShotContext,
) -> SequencerInstruction[np.floating]:
    input_values = evaluate_output(
        mapping.input_,
        required_time_step,
        mapping.input_units,
        prepend,
        append,
        shot_context,
    )
    output_values = input_values.apply(mapping.interpolate)
    if required_unit != mapping.output_units:
        output_values = output_values.apply(
            functools.partial(
                _convert_units,
                input_unit=mapping.output_units,
                output_unit=required_unit,
            )
        )
    return output_values


@evaluate_output.register
def _(
    output_: DeviceTrigger,
    required_time_step: int,
    required_unit: Optional[Unit],
    prepend: int,
    append: int,
    shot_context: ShotContext,
) -> SequencerInstruction[np.bool_]:
    device = output_.device_name
    try:
        device_config = shot_context.get_device_config(device)
    except KeyError:
        raise ValueError(
            f"Could not find device <{device}> to generate trigger "
            f"for output <{output_}>."
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


@evaluate_output.register
def evaluate_advanced_output(
    output_: Advance,
    required_time_step: int,
    required_unit: Optional[Unit],
    prepend: int,
    append: int,
    shot_context: ShotContext,
) -> SequencerInstruction:
    evaluated_advance = _evaluate_expression_in_unit(
        output_.advance, Unit("ns"), shot_context.get_variables()
    )
    number_ticks_to_advance = round(evaluated_advance / required_time_step)
    if number_ticks_to_advance < 0:
        raise ValueError(
            f"Cannot advance by a negative number of time steps "
            f"({number_ticks_to_advance})"
        )
    if number_ticks_to_advance > prepend:
        raise ValueError(
            f"Cannot advance by {number_ticks_to_advance} time steps when only "
            f"{prepend} are available"
        )
    return evaluate_output(
        output_.input_,
        required_time_step,
        required_unit,
        prepend - number_ticks_to_advance,
        append + number_ticks_to_advance,
        shot_context,
    )


@evaluate_output.register
def evaluate_delayed_output(
    output_: Delay,
    required_time_step: int,
    required_unit: Optional[Unit],
    prepend: int,
    append: int,
    shot_context: ShotContext,
) -> SequencerInstruction:
    evaluated_delay = _evaluate_expression_in_unit(
        output_.delay, Unit("ns"), shot_context.get_variables()
    )
    number_ticks_to_delay = round(evaluated_delay / required_time_step)
    if number_ticks_to_delay < 0:
        raise ValueError(
            f"Cannot delay by a negative number of time steps "
            f"({number_ticks_to_delay})"
        )
    return evaluate_output(
        output_.input_,
        required_time_step,
        required_unit,
        prepend + number_ticks_to_delay,
        append - number_ticks_to_delay,
        shot_context,
    )


def evaluate_digital_lane_output(
    lane: DigitalTimeLane, time_step: int, shot_context: ShotContext
) -> SequencerInstruction[np.bool_]:
    assert isinstance(lane, DigitalTimeLane)
    compiler = DigitalLaneCompiler(lane, self.step_names, self.step_durations)
    lane_output = compiler.compile(self.variables, time_step)
    assert lane_output.dtype == np.dtype("bool")
    return lane_output


def evaluate_analog_lane_output(
    lane: AnalogTimeLane,
    time_step: int,
    target_unit: Optional[Unit],
    shot_context: ShotContext,
) -> SequencerInstruction[np.floating]:
    return


class SequencerCompilationError(Exception):
    pass


def _evaluate_max_advance_and_delay(
    channel_function: ChannelOutput,
    time_step: int,
    variables: Mapping[DottedVariableName, Any],
) -> tuple[int, int]:
    if is_value_source(channel_function):
        return 0, 0
    elif isinstance(channel_function, TimeIndependentMapping):
        advances_and_delays = [
            _evaluate_max_advance_and_delay(input_, time_step, variables)
            for input_ in channel_function.inputs()
        ]
        advances, delays = zip(*advances_and_delays)
        return max(advances), max(delays)
    elif isinstance(channel_function, Advance):
        advance = _evaluate_expression_in_unit(
            channel_function.advance, Unit("ns"), variables
        )
        if advance < 0:
            raise ValueError(f"Advance must be a positive number.")
        advance_ticks = round(advance / time_step)
        input_advance, input_delay = _evaluate_max_advance_and_delay(
            channel_function.input_, time_step, variables
        )
        return advance_ticks + input_advance, input_delay
    elif isinstance(channel_function, Delay):
        delay = _evaluate_expression_in_unit(
            channel_function.delay, Unit("ns"), variables
        )
        if delay < 0:
            raise ValueError(f"Delay must be a positive number.")
        delay_ticks = round(delay / time_step)
        input_advance, input_delay = _evaluate_max_advance_and_delay(
            channel_function.input_, time_step, variables
        )
        return input_advance, delay_ticks + input_delay
    else:
        raise NotImplementedError(
            f"Cannot evaluate max advance and delay for {channel_function}"
        )


def _evaluate_expression_in_unit(
    expression: Expression,
    required_unit: Optional[Unit],
    variables: Mapping[DottedVariableName, Any],
) -> np.floating:
    value = expression.evaluate(variables)
    magnitude = magnitude_in_unit(value, required_unit)
    return magnitude


def _convert_channel_instruction(
    instruction: SequencerInstruction, channel: ChannelConfiguration
) -> SequencerInstruction:
    match channel:
        case DigitalChannelConfiguration():
            return instruction.as_type(np.dtype(np.bool_))
        case AnalogChannelConfiguration():
            return instruction.as_type(np.dtype(np.float64))
        case _:
            raise NotImplementedError


def _convert_units(
    array: np.ndarray, input_unit: Optional[str], output_unit: Optional[str]
) -> np.ndarray:
    if input_unit == output_unit:
        return array
    return magnitude_in_unit(add_unit(array, input_unit), output_unit)  # type: ignore
