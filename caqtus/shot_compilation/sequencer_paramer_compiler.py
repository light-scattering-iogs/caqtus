from __future__ import annotations

import functools
import logging
from collections.abc import Sequence, Mapping
from typing import TypedDict, Optional

import numpy as np

from caqtus.device import DeviceName, DeviceConfigurationAttrs, get_configurations_by_type
from caqtus.device.camera import CameraConfiguration
from caqtus.device.sequencer import (
    SequencerConfiguration,
    SoftwareTrigger,
    ChannelConfiguration,
    DigitalChannelConfiguration,
    ExternalClockOnChange,
    ExternalTriggerStart,
)
from caqtus.device.sequencer.configuration import Advance, Delay, TimeIndependentMapping
from caqtus.device.sequencer.configuration import (
    AnalogChannelConfiguration,
    Constant,
    LaneValues,
    DeviceTrigger,
    ChannelOutput,
    CalibratedAnalogMapping,
    is_value_source,
)
from caqtus.device.sequencer.instructions import (
    SequencerInstruction,
    with_name,
    stack_instructions,
    Pattern,
    Repeat,
    Concatenate,
    join,
)
from caqtus.session.shot import TimeLane, DigitalTimeLane, AnalogTimeLane, CameraTimeLane
from caqtus.types.expression import Expression
from caqtus.types.parameter import add_unit, magnitude_in_unit
from caqtus.types.units import Unit
from caqtus.utils import add_exc_note
from .lane_compilers import DigitalLaneCompiler, AnalogLaneCompiler, CameraLaneCompiler
from .lane_compilers import evaluate_step_durations
from .lane_compilers.timing import number_ticks, ns, get_step_bounds
from caqtus.types.units.unit_namespace import units
from .variable_namespace import VariableNamespace

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SequencerParameterCompiler:
    def __init__(
        self,
        step_names: Sequence[str],
        step_durations: Sequence[Expression],
        lanes: Mapping[str, TimeLane],
        devices: Mapping[DeviceName, DeviceConfigurationAttrs],
    ):
        self.steps = list(zip(step_names, step_durations))
        self.lanes = lanes
        self.sequencer_configurations = get_configurations_by_type(
            devices, SequencerConfiguration
        )
        self.device_configurations = devices
        self.root_sequencer = find_root_sequencer(self.sequencer_configurations)

    def compile(
        self, variables: VariableNamespace
    ) -> dict[DeviceName, SequencerParameters]:
        single_shot_compiler = SingleShotCompiler(
            [name for name, _ in self.steps],
            [duration for _, duration in self.steps],
            self.lanes,
            self.sequencer_configurations,
            self.device_configurations,
            self.root_sequencer,
            variables,
        )
        return single_shot_compiler.compile()


class SingleShotCompiler:
    def __init__(
        self,
        step_names: Sequence[str],
        step_durations: Sequence[Expression],
        lanes: Mapping[str, TimeLane],
        sequencer_configurations: Mapping[DeviceName, SequencerConfiguration],
        devices: Mapping[DeviceName, DeviceConfigurationAttrs],
        root_sequencer: DeviceName,
        variables: VariableNamespace,
    ):
        steps = list(zip(step_names, step_durations))
        durations = evaluate_step_durations(steps, variables)
        self.step_names = step_names
        self.step_durations = step_durations
        # Here we need to compute the shot duration the exact same way as in the
        # step bounds.
        # In particular, get_step_bounds(durations)[-1] is not the same in general
        # as sum(durations) due to floating point errors.
        self.shot_duration = get_step_bounds(durations)[-1]
        self.variables = variables
        self.sequencer_configurations = sequencer_configurations
        self.lanes = lanes
        self.root_sequencer = root_sequencer
        self.devices = devices

        self.sequencer_instructions: dict[DeviceName, SequencerInstruction] = {}
        self.used_lanes: set[str] = set()

    def compile(self) -> dict[DeviceName, SequencerParameters]:
        self.compile_sequencer_instruction(self.root_sequencer)
        unreached_sequencers = set(self.sequencer_configurations.keys()) - set(
            self.sequencer_instructions.keys()
        )

        if unreached_sequencers:
            error = ValueError(
                f"There is no trigger relationship from the root sequencer "
                f"'{self.root_sequencer}' to the following sequencers: "
                f"{unreached_sequencers}"
            )
            error.add_note(
                "Check that the above sequencers are triggered by the root "
                "sequencer or one of its children"
            )
            raise error

        digital_lanes = {
            name
            for name, lane in self.lanes.items()
            if isinstance(lane, DigitalTimeLane)
        }
        analog_lanes = {
            name
            for name, lane in self.lanes.items()
            if isinstance(lane, AnalogTimeLane)
        }

        unused_lanes = (digital_lanes | analog_lanes) - self.used_lanes
        if unused_lanes:
            raise ValueError(
                f"The following lanes where not used when compiling the shot: "
                f"{unused_lanes}"
            )

        return {
            sequencer_name: {"sequence": instruction}
            for sequencer_name, instruction in self.sequencer_instructions.items()
        }

    def compile_sequencer_instruction(
        self, sequencer_name: DeviceName
    ) -> SequencerInstruction:
        if sequencer_name in self.sequencer_instructions:
            return self.sequencer_instructions[sequencer_name]

        sequencer_config = self.sequencer_configurations[sequencer_name]
        channel_instructions = []
        for channel_number, channel in enumerate(sequencer_config.channels):
            if isinstance(channel, AnalogChannelConfiguration):
                required_unit = channel.output_unit
            else:
                required_unit = None
            try:
                max_advance, max_delay = self.find_max_advance_and_delays(
                    sequencer_config
                )
                output_values = self.evaluate_output(
                    channel.output,
                    sequencer_config.time_step,
                    required_unit,
                    max_advance,
                    max_delay,
                )
            except Exception as e:
                raise SequencerCompilationError(
                    f"Error occurred when evaluating output for channel "
                    f"{channel_number} ({channel}) of sequencer "
                    f"{sequencer_name}"
                ) from e
            instruction = self.convert_channel_instruction(output_values, channel)
            channel_instructions.append(with_name(instruction, f"ch {channel_number}"))
        stacked = stack_instructions(channel_instructions)
        self.sequencer_instructions[sequencer_name] = stacked
        return stacked

    def find_max_advance_and_delays(
        self, sequencer_config: SequencerConfiguration
    ) -> tuple[int, int]:
        advances_and_delays = [
            evaluate_max_advance_and_delay(
                channel.output, sequencer_config.time_step, self.variables
            )
            for channel in sequencer_config.channels
        ]
        advances, delays = zip(*advances_and_delays)
        return max(advances), max(delays)

    @functools.singledispatchmethod
    def evaluate_output(
        self,
        output_: ChannelOutput,
        required_time_step: int,
        required_unit: Optional[Unit],
        prepend: int,
        append: int,
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
        """

        raise NotImplementedError(f"Cannot evaluate output <{output_}>")

    @evaluate_output.register
    def _(
        self,
        output_: Constant,
        required_time_step: int,
        required_unit: Optional[Unit],
        prepend: int,
        append: int,
    ) -> SequencerInstruction:
        """Evaluate a constant output.

        Returns an instruction that has constant values for the entire shot duration.
        The constant value is obtained by evaluating the value stored in the constant
        output within the shot namespace.
        Note that `constant` refers to a value constant in shot time, not necessarily
        constant across shots.
        """

        length = (
            number_ticks(0, self.shot_duration, required_time_step * ns)
            + prepend
            + append
        )
        expression = output_.value
        value = expression.evaluate(self.variables)
        magnitude = magnitude_in_unit(value, required_unit)
        return Pattern([magnitude]) * length

    @evaluate_output.register
    def _(
        self,
        output_: LaneValues,
        required_time_step: int,
        required_unit: Optional[Unit],
        prepend: int,
        append: int,
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
            lane = self.lanes[lane_name]
        except KeyError:
            if output_.default is not None:
                constant = Constant(output_.default)
                return self.evaluate_output(
                    constant, required_time_step, required_unit, prepend, append
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
            self.used_lanes.add(lane_name)
            with add_exc_note(f"When evaluating digital lane <{lane_name}>"):
                lane_values = self.evaluate_digital_lane_output(
                    lane, required_time_step
                )
        elif isinstance(lane, AnalogTimeLane):
            self.used_lanes.add(lane_name)
            with add_exc_note(f"When evaluating analog lane <{lane_name}>"):
                lane_values = self.evaluate_analog_lane_output(
                    lane, required_time_step, required_unit
                )
        else:
            raise TypeError(
                f"Cannot evaluate values of lane with type " f"{type(lane)}"
            )
        prepend_pattern = prepend * Pattern([lane_values[0]])
        append_pattern = append * Pattern([lane_values[-1]])
        return prepend_pattern + lane_values + append_pattern

    def evaluate_digital_lane_output(
        self, lane: DigitalTimeLane, time_step: int
    ) -> SequencerInstruction:
        assert isinstance(lane, DigitalTimeLane)
        compiler = DigitalLaneCompiler(lane, self.step_names, self.step_durations)
        lane_output = compiler.compile(self.variables, time_step)
        assert lane_output.dtype == np.dtype("bool")
        return lane_output

    def evaluate_analog_lane_output(
        self,
        lane: AnalogTimeLane,
        time_step: int,
        target_unit: Optional[Unit],
    ) -> SequencerInstruction[np.floating]:
        compiler = AnalogLaneCompiler(
            lane, self.step_names, self.step_durations, target_unit
        )
        lane_output = compiler.compile(self.variables, time_step)
        return lane_output

    @evaluate_output.register
    def _(
        self,
        mapping: CalibratedAnalogMapping,
        required_time_step: int,
        required_unit: Optional[Unit],
        prepend: int,
        append: int,
    ) -> SequencerInstruction[np.floating]:
        input_values = self.evaluate_output(
            mapping.input_, required_time_step, mapping.input_units, prepend, append
        )
        output_values = input_values.apply(mapping.interpolate)
        if required_unit != mapping.output_units:
            output_values = output_values.apply(
                functools.partial(
                    convert_units,
                    input_unit=mapping.output_units,
                    output_unit=required_unit,
                )
            )
        return output_values

    @evaluate_output.register
    def _(
        self,
        output_: DeviceTrigger,
        required_time_step: int,
        required_unit: Optional[Unit],
        prepend: int,
        append: int,
    ) -> SequencerInstruction[np.bool_]:
        device = output_.device_name
        if device not in self.devices:
            raise ValueError(
                f"Could not find device <{device}> to generate trigger "
                f"for output <{output_}>."
            )
        if required_unit is not None:
            raise ValueError(
                f"Cannot evaluate trigger for device <{device}> with unit "
                f"{required_unit:~}"
            )
        trigger_values = self.evaluate_device_trigger(device, required_time_step)
        return prepend * Pattern([False]) + trigger_values + append * Pattern([False])

    def evaluate_device_trigger(
        self,
        device: DeviceName,
        time_step: int,
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

        device_config = self.devices[device]
        if isinstance(device_config, SequencerConfiguration):
            return self.evaluate_trigger_for_sequencer(
                slave=device, master_time_step=time_step
            )
        elif isinstance(device_config, CameraConfiguration):
            return self.evaluate_trigger_for_camera(device, time_step)
        else:
            length = number_ticks(0, self.shot_duration, time_step * ns)
            high_duration = length // 2
            low_duration = length - high_duration
            if high_duration == 0 or low_duration == 0:
                raise ValueError(
                    "The shot duration is too short to generate a trigger pulse for "
                    f"device '{device}'"
                )
            return Pattern([True]) * high_duration + Pattern([False]) * low_duration

    def evaluate_trigger_for_sequencer(
        self,
        slave: DeviceName,
        master_time_step: int,
    ) -> SequencerInstruction[np.bool_]:
        length = number_ticks(0, self.shot_duration, master_time_step * ns)
        slave_config = self.devices[slave]
        assert isinstance(slave_config, SequencerConfiguration)
        slave_instruction = self.compile_sequencer_instruction(slave)
        if isinstance(slave_config.trigger, ExternalClockOnChange):
            single_clock_pulse = get_master_clock_pulse(
                slave_config.time_step, master_time_step
            )
            instruction = get_adaptive_clock(slave_instruction, single_clock_pulse)[
                :length
            ]
            return instruction
        elif isinstance(slave_config.trigger, ExternalTriggerStart):
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
                f"Cannot evaluate trigger for trigger of type "
                f"{type(slave_config.trigger)}"
            )

    def evaluate_trigger_for_camera(
        self, device: DeviceName, time_step: int
    ) -> SequencerInstruction[np.bool_]:
        try:
            lane = self.lanes[device]
        except KeyError:
            # If there is no lane with the name of this camera, it probably means that
            # the camera is not used in this shot, so instead of raising an error, we
            # just return no trigger, but I don't know if it is the best option.
            length = number_ticks(0, self.shot_duration, time_step * ns)
            return Pattern([False]) * length
        if not isinstance(lane, CameraTimeLane):
            raise ValueError(
                f"Asked to generate trigger for device '{device}', which is a "
                f"camera, but the lane with this name is not a camera lane "
                f"(got {type(lane)})"
            )
        camera_compiler = CameraLaneCompiler(lane, self.step_names, self.step_durations)
        return camera_compiler.compile_trigger(self.variables, time_step)

    @evaluate_output.register
    def evaluate_advanced_output(
        self,
        output_: Advance,
        required_time_step: int,
        required_unit: Optional[Unit],
        prepend: int,
        append: int,
    ) -> SequencerInstruction:
        evaluated_advance = _evaluate_expression_in_unit(
            output_.advance, Unit("ns"), self.variables
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
        return self.evaluate_output(
            output_.input_,
            required_time_step,
            required_unit,
            prepend - number_ticks_to_advance,
            append + number_ticks_to_advance,
        )

    @evaluate_output.register
    def evaluate_delayed_output(
        self,
        output_: Delay,
        required_time_step: int,
        required_unit: Optional[Unit],
        prepend: int,
        append: int,
    ) -> SequencerInstruction:
        evaluated_delay = _evaluate_expression_in_unit(
            output_.delay, Unit("ns"), self.variables
        )
        number_ticks_to_delay = round(evaluated_delay / required_time_step)
        if number_ticks_to_delay < 0:
            raise ValueError(
                f"Cannot delay by a negative number of time steps "
                f"({number_ticks_to_delay})"
            )
        return self.evaluate_output(
            output_.input_,
            required_time_step,
            required_unit,
            prepend + number_ticks_to_delay,
            append - number_ticks_to_delay,
        )

    def convert_channel_instruction(
        self, instruction: SequencerInstruction, channel: ChannelConfiguration
    ) -> SequencerInstruction:
        match channel:
            case DigitalChannelConfiguration():
                return instruction.as_type(np.dtype(np.bool_))
            case AnalogChannelConfiguration():
                return instruction.as_type(np.dtype(np.float64))
            case _:
                raise NotImplementedError


def convert_units(
    array: np.ndarray, input_unit: Optional[str], output_unit: Optional[str]
) -> np.ndarray:
    if input_unit == output_unit:
        return array
    return magnitude_in_unit(add_unit(array, input_unit), output_unit)  # type: ignore


def find_root_sequencer(
    configs: Mapping[DeviceName, SequencerConfiguration]
) -> DeviceName:
    """Find sequencer that is the trigger source of all other sequencers.

    This function looks in the sequencer configurations passed to find a sequencer that
    has a software trigger source.

    Args:
        configs: A mapping from device names to sequencer configurations.

    Returns:
        The name of the root sequencer.

    Raises:
        ValueError: If no root sequencer is found or if more than one sequencer is
        software triggered.
    """

    software_triggered = [
        name
        for name, config in configs.items()
        if isinstance(config.trigger, SoftwareTrigger)
    ]

    if len(software_triggered) == 0:
        raise ValueError("No root sequencer found")
    elif len(software_triggered) > 1:
        raise ValueError(f"More than one root sequencer found: {software_triggered}")

    return software_triggered[0]


class SequencerParameters(TypedDict):
    sequence: SequencerInstruction


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


@functools.singledispatch
def get_adaptive_clock(
    slave_instruction: SequencerInstruction, clock_pulse: SequencerInstruction
) -> SequencerInstruction:
    raise NotImplementedError(f"Target sequence {slave_instruction} not implemented")


@get_adaptive_clock.register
def _(
    target_sequence: Pattern, clock_pulse: SequencerInstruction
) -> SequencerInstruction:
    return clock_pulse * len(target_sequence)


@get_adaptive_clock.register
def _(
    target_sequence: Concatenate, clock_pulse: SequencerInstruction
) -> SequencerInstruction:
    return join(
        *(
            get_adaptive_clock(sequence, clock_pulse)
            for sequence in target_sequence.instructions
        )
    )


@get_adaptive_clock.register
def _(
    target_sequence: Repeat, clock_pulse: SequencerInstruction
) -> SequencerInstruction:
    if len(target_sequence.instruction) == 1:
        return clock_pulse + Pattern([False]) * (
            (len(target_sequence) - 1) * len(clock_pulse)
        )
    else:
        raise NotImplementedError(
            "Only one instruction is supported in a repeat block at the moment"
        )


class SequencerCompilationError(Exception):
    pass


def evaluate_max_advance_and_delay(
    channel_function: ChannelOutput, time_step: int, variables: VariableNamespace
) -> tuple[int, int]:
    if is_value_source(channel_function):
        return 0, 0
    elif isinstance(channel_function, TimeIndependentMapping):
        advances_and_delays = [
            evaluate_max_advance_and_delay(input_, time_step, variables)
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
        input_advance, input_delay = evaluate_max_advance_and_delay(
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
        input_advance, input_delay = evaluate_max_advance_and_delay(
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
    variables: VariableNamespace,
) -> np.floating:
    value = expression.evaluate(variables.dict())
    magnitude = magnitude_in_unit(value, required_unit)
    return magnitude
