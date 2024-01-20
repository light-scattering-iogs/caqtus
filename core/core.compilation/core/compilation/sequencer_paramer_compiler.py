from __future__ import annotations

import functools
import logging
from collections.abc import Sequence, Mapping
from typing import TypedDict, Optional

import attrs
import numpy as np
from core.compilation import VariableNamespace
from core.device import DeviceName, DeviceConfigurationAttrs, get_configurations_by_type
from core.device.sequencer import (
    SequencerConfiguration,
    SoftwareTrigger,
    ChannelConfiguration,
    DigitalChannelConfiguration,
    ExternalClockOnChange,
)
from core.device.sequencer.configuration import (
    AnalogChannelConfiguration,
    Constant,
    LaneValues,
    DeviceTrigger,
    ChannelOutput,
)
from core.device.sequencer.instructions import (
    SequencerInstruction,
    with_name,
    stack_instructions,
    Pattern,
    Repeat,
    Concatenate,
    join,
)
from core.session.shot import TimeLane, DigitalTimeLane, AnalogTimeLane
from core.types.expression import Expression
from core.types.parameter import add_unit, magnitude_in_unit, get_unit
from core.types.units import Unit

from .lane_compilers import DigitalLaneCompiler, AnalogLaneCompiler
from .lane_compilers import evaluate_step_durations
from .lane_compilers.timing import number_ticks, ns
from .unit_namespace import units

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@attrs.frozen
class ChannelOutputResult:
    instruction: SequencerInstruction
    unit: Optional[Unit]

    @property
    def dtype(self):
        return self.instruction.dtype


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
        self.root_sequencer = find_root_sequencer(self.sequencer_configurations)

    def compile(
        self, variables: VariableNamespace
    ) -> dict[DeviceName, SequencerParameters]:
        single_shot_compiler = SingleShotCompiler(
            [name for name, _ in self.steps],
            [duration for _, duration in self.steps],
            self.lanes,
            self.sequencer_configurations,
            self.sequencer_configurations,
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
        self.shot_duration = sum(durations)
        self.variables = variables
        self.sequencer_configurations = sequencer_configurations
        self.lanes = lanes
        self.root_sequencer = root_sequencer
        self.devices = devices

        self.sequencer_instructions: dict[DeviceName, SequencerInstruction] = {}
        self.used_lanes = set()

    def compile(self) -> dict[DeviceName, SequencerParameters]:
        self.compile_sequencer_instruction(self.root_sequencer)
        unreached_sequencers = set(self.sequencer_configurations.keys()) - set(
            self.sequencer_instructions.keys()
        )

        if unreached_sequencers:
            raise ValueError(
                f"Could not trigger sequencers {unreached_sequencers} from root "
                f"sequencer {self.root_sequencer}"
            )

        unused_lanes = set(self.lanes.keys()) - self.used_lanes
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
        try:
            if sequencer_name in self.sequencer_instructions:
                return self.sequencer_instructions[sequencer_name]

            sequencer_config = self.sequencer_configurations[sequencer_name]
            channel_instructions = []
            for channel_number, channel in enumerate(sequencer_config.channels):
                if isinstance(channel, AnalogChannelConfiguration):
                    required_unit = channel.output_unit
                else:
                    required_unit = None
                output_values = self.evaluate_output(
                    channel.output, sequencer_config.time_step, required_unit
                )
                instruction = self.convert_to_channel_instruction(
                    output_values, channel
                )
                channel_instructions.append(
                    with_name(instruction, f"ch {channel_number}")
                )
            stacked = stack_instructions(channel_instructions)
            self.sequencer_instructions[sequencer_name] = stacked
            return stacked
        except Exception as e:
            raise SequencerCompilationError(
                f"Couldn't compile instruction for sequencer {sequencer_name}"
            ) from e

    @functools.singledispatchmethod
    def evaluate_output(
        self,
        output_: ChannelOutput,
        required_time_step: int,
        required_unit: Optional[Unit],
    ) -> ChannelOutputResult:
        raise NotImplementedError(f"Cannot evaluate output <{output_}>")

    @evaluate_output.register
    def _(
        self, output_: Constant, required_time_step: int, required_unit: Optional[Unit]
    ) -> ChannelOutputResult:
        length = number_ticks(0, self.shot_duration, required_time_step * ns)

        expression = output_.value
        value = expression.evaluate(self.variables | units)
        magnitude = magnitude_in_unit(value, required_unit)
        return ChannelOutputResult(
            instruction=Pattern([magnitude]) * length,
            unit=required_unit,
        )

    @evaluate_output.register
    def _(
        self,
        output_: LaneValues,
        required_time_step: int,
        required_unit: Optional[Unit],
    ) -> ChannelOutputResult:
        lane_name = output_.lane
        try:
            lane = self.lanes[lane_name]
        except KeyError:
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
            evaluated = self.evaluate_digital_lane_output(lane, required_time_step)
            self.used_lanes.add(lane_name)
            return evaluated
        elif isinstance(lane, AnalogTimeLane):
            self.used_lanes.add(lane_name)
            return self.evaluate_analog_lane_output(
                lane, required_time_step, required_unit
            )
        else:
            raise TypeError(
                f"Cannot evaluate values of lane with type " f"{type(lane)}"
            )

    def evaluate_digital_lane_output(
        self, lane: DigitalTimeLane, time_step: int
    ) -> ChannelOutputResult:
        assert isinstance(lane, DigitalTimeLane)
        compiler = DigitalLaneCompiler(lane, self.step_names, self.step_durations)
        lane_output = compiler.compile(self.variables, time_step)
        assert lane_output.dtype == np.dtype("bool")
        return ChannelOutputResult(
            instruction=lane_output,
            unit=None,
        )

    def evaluate_analog_lane_output(
        self,
        lane: AnalogTimeLane,
        time_step: int,
        target_unit: Optional[Unit],
    ) -> ChannelOutputResult:
        compiler = AnalogLaneCompiler(
            lane, self.step_names, self.step_durations, target_unit
        )
        lane_output = compiler.compile(self.variables, time_step)
        return ChannelOutputResult(
            instruction=lane_output,
            unit=target_unit,
        )

    @evaluate_output.register
    def _(
        self,
        output_: DeviceTrigger,
        required_time_step: int,
        required_unit: Optional[Unit],
    ) -> ChannelOutputResult:
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
        return self.evaluate_device_trigger(device, required_time_step)

    def evaluate_device_trigger(
        self,
        device: DeviceName,
        time_step: int,
    ) -> ChannelOutputResult:
        device_config = self.devices[device]
        if isinstance(device_config, SequencerConfiguration):
            return self.evaluate_trigger_for_sequencer(
                slave=device, master_time_step=time_step
            )
        else:
            raise NotImplementedError(
                f"Cannot evaluate trigger for device of type {type(device_config)}"
            )

    def evaluate_trigger_for_sequencer(
        self,
        slave: DeviceName,
        master_time_step: int,
    ) -> ChannelOutputResult:
        length = number_ticks(0, self.shot_duration, master_time_step * ns)
        slave_config = self.devices[slave]
        assert isinstance(slave_config, SequencerConfiguration)
        if isinstance(slave_config.trigger, ExternalClockOnChange):
            _, high, low = high_low_clicks(slave_config.time_step, master_time_step)
            single_clock_pulse = Pattern([True]) * high + Pattern([False]) * low
            slave_instruction = self.compile_sequencer_instruction(slave)
            instruction = get_adaptive_clock(slave_instruction, single_clock_pulse)[
                :length
            ]
            return ChannelOutputResult(
                instruction=instruction,
                unit=None,
            )
        else:
            raise NotImplementedError(
                f"Cannot evaluate trigger for trigger of type "
                f"{type(slave_config.trigger)}"
            )

    def convert_to_channel_instruction(
        self, output_: ChannelOutputResult, channel: ChannelConfiguration
    ) -> SequencerInstruction:
        match channel:
            case DigitalChannelConfiguration():
                if not output_.dtype == np.dtype("bool"):
                    raise TypeError(
                        f"Channel {channel.description} is digital but its output "
                        f"<{channel.output}> is not boolean and has dtype "
                        f"{output_.dtype}"
                    )
                if output_.unit is not None:
                    raise TypeError(
                        f"Channel {channel.description} is digital but its output "
                        f"<{channel.output}> has unit {output_.unit}"
                    )
                return output_.instruction
            case AnalogChannelConfiguration(output_unit=output_unit):
                return output_.instruction.apply(
                    functools.partial(
                        convert_units, input_unit=output_.unit, output_unit=output_unit
                    )
                )
            case _:
                raise NotImplementedError


def convert_units(
    array: np.ndarray, input_unit: Optional[str], output_unit: str
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
    slave_instruction: SequencerInstruction, slave_clock_pulse: SequencerInstruction
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
