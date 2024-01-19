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
)
from core.device.sequencer.configuration import (
    AnalogChannelConfiguration,
    Constant,
    LaneValues,
    DeviceTrigger,
)
from core.device.sequencer.instructions import (
    SequencerInstruction,
    with_name,
    stack_instructions,
    Pattern,
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
            output_ = self.evaluate_output(channel, sequencer_config)
            instruction = self.convert_to_channel_instruction(output_, channel)
            channel_instructions.append(with_name(instruction, f"ch {channel_number}"))
        stacked = stack_instructions(channel_instructions)
        self.sequencer_instructions[sequencer_name] = stacked
        return stacked

    def evaluate_output(
        self, channel: ChannelConfiguration, sequencer_config: SequencerConfiguration
    ) -> ChannelOutput:
        time_step = sequencer_config.time_step
        length = number_ticks(0, self.shot_duration, time_step * ns)

        match channel.output:
            case Constant(expression):
                value = expression.evaluate(self.variables | units)
                unit = get_unit(value)
                magnitude = magnitude_in_unit(value, unit)
                return ChannelOutput(
                    instruction=Pattern([magnitude]) * length,
                    unit=unit,
                )
            case LaneValues(lane_name):
                try:
                    lane = self.lanes[lane_name]
                except KeyError:
                    raise ValueError(
                        f"Could not find lane <{lane_name}> for channel "
                        f"<{channel.description}>"
                    )
                if isinstance(lane, DigitalTimeLane):
                    return self.evaluate_digital_lane_output(lane, sequencer_config)
                elif isinstance(lane, AnalogTimeLane):
                    if not isinstance(channel, AnalogChannelConfiguration):
                        raise TypeError(
                            f"Cannot evaluate analog lane <{lane_name}> for channel "
                            f"<{channel.description}> with type {type(channel)}"
                        )
                    return self.evaluate_analog_lane_output(
                        lane, sequencer_config, channel.output_unit
                    )
                else:
                    raise TypeError(
                        f"Cannot evaluate values of lane with type " f"{type(lane)}"
                    )
            case DeviceTrigger(device_name):
                device_config = self.devices[device_name]
                return self.evaluate_device_trigger(device_config, sequencer_config)
            case _:
                raise NotImplementedError

    def evaluate_digital_lane_output(
        self, lane: DigitalTimeLane, sequencer_config: SequencerConfiguration
    ) -> ChannelOutput:
        compiler = DigitalLaneCompiler(lane, self.step_names, self.step_durations)
        lane_output = compiler.compile(self.variables, sequencer_config.time_step)
        return ChannelOutput(
            instruction=lane_output,
            unit=None,
        )

    def evaluate_analog_lane_output(
        self,
        lane: AnalogTimeLane,
        sequencer_config: SequencerConfiguration,
        target_unit: Optional[Unit],
    ) -> ChannelOutput:
        compiler = AnalogLaneCompiler(
            lane, self.step_names, self.step_durations, target_unit
        )
        lane_output = compiler.compile(self.variables, sequencer_config.time_step)
        return ChannelOutput(
            instruction=lane_output,
            unit=target_unit,
        )

    def convert_to_channel_instruction(
        self, output_: ChannelOutput, channel: ChannelConfiguration
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
                        convert_units, input_units=output_.unit, output_unit=output_unit
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


@attrs.frozen
class ChannelOutput:
    instruction: SequencerInstruction
    unit: Optional[Unit]

    @property
    def dtype(self):
        return self.instruction.dtype
