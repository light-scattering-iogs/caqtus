import logging
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from analog_lane.configuration import AnalogLane, Ramp
from camera_lane.configuration import CameraLane, TakePicture
from device.configuration import DeviceName
from experiment.configuration import (
    ExperimentConfig,
    DeviceParameter,
)
from expression import Expression
from lane.configuration import Lane
from sequence.configuration import ShotConfiguration
from sequencer.channel import ChannelInstruction, ChannelPattern
from sequencer.configuration import SequencerConfiguration, ChannelConfiguration
from sequencer.instructions import ChannelLabel, SequencerInstruction
from tweezer_arranger_lane.configuration import TweezerArrangerLane
from variable.namespace import VariableNamespace
from .camera_instruction import CameraInstruction
from .clock_instruction import ClockInstruction
from .compile_lane import (
    compile_lane,
    empty_channel_instruction,
    get_step_starts,
    compile_camera_instruction,
    compile_clock_instruction,
)
from .compile_steps import compile_step_durations

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@dataclass
class StepProperties:
    name: str
    duration: float
    analog_times: Optional[np.ndarray] = None


def compute_shot_parameters(
    experiment_config: ExperimentConfig,
    shot_config: ShotConfiguration,
    variables: VariableNamespace,
) -> dict[DeviceName, dict[DeviceParameter, Any]]:
    """Compute the parameters to be applied to the devices before a shot."""

    result: dict[DeviceName, dict[DeviceParameter, Any]] = {}

    camera_instructions = compute_camera_instructions(shot_config, variables)

    result |= get_camera_parameters(camera_instructions)

    sequencer_configs = experiment_config.get_device_configs(SequencerConfiguration)
    clock_requirements = compile_clock_requirements(
        sequencer_configs, shot_config, variables
    )
    sequencer_instructions = {
        sequencer_name: compile_sequencer_instructions(
            sequencer_config,
            shot_config,
            variables,
            camera_instructions,
            clock_requirements,
        )
        for sequencer_name, sequencer_config in sequencer_configs.items()
    }

    sequencer_parameters = {
        sequencer_name: {
            DeviceParameter("sequence"): convert_to_sequence(
                instructions, sequencer_configs[sequencer_name]
            )
        }
        for sequencer_name, instructions in sequencer_instructions.items()
    }

    result |= sequencer_parameters
    result |= compute_tweezer_arranger_instructions(shot_config, variables)

    return result


def compile_sequencer_instructions(
    sequencer_config: SequencerConfiguration,
    shot_config: ShotConfiguration,
    variables: VariableNamespace,
    camera_instructions: Mapping[DeviceName, CameraInstruction],
    clock_requirements: dict[DeviceName, Sequence[ClockInstruction]],
) -> dict[ChannelLabel, ChannelInstruction]:
    step_durations = compile_step_durations(
        shot_config.step_names, shot_config.step_durations, variables
    )
    instructions: dict[ChannelLabel, ChannelInstruction] = {}

    for channel_number, channel in enumerate(sequencer_config.channels):
        instructions[ChannelLabel(channel_number)] = compile_channel_instruction(
            channel,
            sequencer_config,
            step_durations,
            variables,
            shot_config,
            camera_instructions,
            clock_requirements,
        )
    max_delay = round_to_ns(sequencer_config.get_maximum_delay())
    for channel_number, channel in enumerate(sequencer_config.channels):
        delay = round_to_ns(channel.delay)
        instruction = instructions[ChannelLabel(channel_number)]
        pre_step = ChannelPattern([instruction.first_value()]) * delay
        post_step = ChannelPattern([instruction.last_value()]) * (max_delay - delay)
        instructions[ChannelLabel(channel_number)] = pre_step + instruction + post_step

    return instructions


def round_to_ns(value: float) -> int:
    ns = 1e-9
    return round(value / ns)


def compile_channel_instruction(
    channel: ChannelConfiguration,
    sequencer_config: SequencerConfiguration,
    step_durations: Sequence[float],
    variables: VariableNamespace,
    shot_config: ShotConfiguration,
    camera_instructions: Mapping[DeviceName, CameraInstruction],
    clock_requirements: dict[DeviceName, Sequence[ClockInstruction]],
) -> ChannelInstruction:
    if channel.has_special_purpose():
        target = DeviceName(str(channel.description))
        if target in camera_instructions:
            instruction = compile_camera_instruction(
                camera_instructions[target], sequencer_config.time_step
            )
        elif target in clock_requirements:
            instruction = compile_clock_instruction(
                clock_requirements[target], sequencer_config.time_step
            )
        elif channel.is_unused():
            instruction = empty_channel_instruction(
                channel.default_value, step_durations, sequencer_config.time_step
            )
        else:
            instruction = empty_channel_instruction(
                channel.default_value, step_durations, sequencer_config.time_step
            )
    else:
        if lane := shot_config.find_lane(channel.description):
            instruction = compile_lane(
                lane, step_durations, sequencer_config.time_step, variables
            )
        else:
            instruction = empty_channel_instruction(
                channel.default_value, step_durations, sequencer_config.time_step
            )

    instruction = instruction.apply(channel.output_mapping.convert)
    return instruction


def convert_to_sequence(
    channel_instructions: dict[ChannelLabel, ChannelInstruction],
    sequencer_config: SequencerConfiguration,
) -> SequencerInstruction:
    channel_label = ChannelLabel(0)
    sequence = SequencerInstruction.from_channel_instruction(
        channel_label, channel_instructions[channel_label]
    )
    for channel_index in range(1, sequencer_config.number_channels):
        channel_label = ChannelLabel(channel_index)
        sequence = sequence.add_channel_instruction(
            channel_label, channel_instructions[channel_label]
        )
    return sequence


def compute_camera_instructions(
    shot_config: ShotConfiguration, variables: VariableNamespace
) -> dict[DeviceName, CameraInstruction]:
    """Compute the parameters to be applied to each camera.

    Returns:
        A dictionary mapping camera names to their parameters
    """

    step_durations = compile_step_durations(
        shot_config.step_names, shot_config.step_durations, variables
    )

    step_bounds = get_step_starts(step_durations)

    result = {}
    shot_duration = sum(step_durations)

    camera_lanes = shot_config.get_lanes(CameraLane)
    for lane_name, lane in camera_lanes.items():
        triggers = []
        for value, start, stop in lane.get_value_spans():
            if isinstance(value, TakePicture):
                state = True
            else:
                state = False
            duration = sum(step_durations[start:stop])
            triggers.append((state, step_bounds[start], step_bounds[stop], duration))
        instructions = CameraInstruction(
            timeout=shot_duration
            + 1,  # add a second to be safe and not timeout too early if the shot takes time to start
            triggers=triggers,
        )
        result[DeviceName(lane_name)] = instructions
    return result


def get_camera_parameters(
    camera_instructions: Mapping[DeviceName, CameraInstruction]
) -> dict[DeviceName, dict[DeviceParameter, Any]]:
    """Extract the parameters to be applied to each camera from the instructions.

    This function only keeps the parameters to be applied to a camera. It removes the triggers because they will be used
    to program a digital sequencer and not the cameras themselves.

    Returns:
        A dictionary mapping camera names to their parameters
    """

    result = {}

    for camera, instruction in camera_instructions.items():
        exposures = [
            duration for expose, start, stop, duration in instruction.triggers if expose
        ]
        result[camera] = {
            DeviceParameter("timeout"): instruction.timeout,
            DeviceParameter("exposures"): exposures,
        }

    return result


def compile_clock_requirements(
    sequencer_configs: Mapping[DeviceName, SequencerConfiguration],
    shot_config: ShotConfiguration,
    variables: VariableNamespace,
) -> dict[DeviceName, list[ClockInstruction]]:
    # TODO: make this more general to more devices.

    step_durations = compile_step_durations(
        shot_config.step_names, shot_config.step_durations, variables
    )
    step_bounds = get_step_starts(step_durations)

    sequencer = DeviceName("NI6738 card")
    sequencer_config = sequencer_configs[sequencer]
    sequencer_clock_instructions = []
    for step_index, clock_instruction in enumerate(
        compute_clock_step_requirements(
            sequencer_config,
            shot_config,
        )
    ):
        sequencer_clock_instructions.append(
            ClockInstruction(
                start=step_bounds[step_index],
                stop=step_bounds[step_index + 1],
                time_step=sequencer_config.time_step,
                order=clock_instruction,
            )
        )
    arranger = DeviceName("Tweezer Arranger")
    arranger_clock_instructions = [
        ClockInstruction(
            start=step_bounds[0],
            stop=step_bounds[-1],
            time_step=1000,
            order=ClockInstruction.StepInstruction.TriggerStart,
        )
    ]

    pulse_streamer = DeviceName("Swabian pulse streamer")
    pulse_streamer_clock_instructions = [
        ClockInstruction(
            start=step_bounds[0],
            stop=step_bounds[-1],
            time_step=1000,
            order=ClockInstruction.StepInstruction.TriggerStart,
        )
    ]

    return {
        sequencer: sequencer_clock_instructions,
        arranger: arranger_clock_instructions,
        pulse_streamer: pulse_streamer_clock_instructions,
    }


def compute_clock_step_requirements(
    sequencer_config: SequencerConfiguration,
    shot_config: ShotConfiguration,
) -> list[ClockInstruction.StepInstruction]:
    lanes = {
        channel.description: lane
        for channel in sequencer_config.get_lane_channels()
        if (lane := shot_config.find_lane(channel.description))
    }

    result = []
    for step in range(shot_config.number_steps):
        instruction = ClockInstruction.StepInstruction.NoClock
        for lane in lanes.values():
            if is_constant(lane, step):
                instruction = ClockInstruction.StepInstruction.TriggerStart
            else:
                result.append(ClockInstruction.StepInstruction.Clock)
                break
        else:
            result.append(instruction)
    return result


def start_tick(time: float, time_step: float) -> int:
    return math.ceil(time / time_step)


def compute_tweezer_arranger_instructions(
    shot_config: ShotConfiguration, variables: VariableNamespace
) -> dict[DeviceName, dict[DeviceParameter, Any]]:
    step_durations = compile_step_durations(
        shot_config.step_names, shot_config.step_durations, variables
    )

    step_bounds = get_step_starts(step_durations)

    result = {}

    tweezer_arranger_lanes = shot_config.get_lanes(TweezerArrangerLane)
    for lane_name, lane in tweezer_arranger_lanes.items():
        durations = []
        for _, start, stop in lane.get_value_spans():
            durations.append(step_bounds[stop] - step_bounds[start])
        result[DeviceName(lane_name)] = {
            DeviceParameter("tweezer_sequence_durations"): durations
        }
    return result


def get_constant_steps(
    shot_config: ShotConfiguration,
    sequencer_config: SequencerConfiguration,
) -> list[bool]:
    lanes = {
        channel.description: lane
        for channel in sequencer_config.get_lane_channels()
        if (lane := shot_config.find_lane(channel.description))
    }

    result = []
    for step in range(shot_config.number_steps):
        result.append(all(is_constant(lane, step) for lane in lanes.values()))
    return result


def is_constant(lane: Lane, step: int) -> bool:
    if isinstance(lane, AnalogLane):
        value = lane.get_effective_value(step)
        if isinstance(value, Ramp):
            return False
        elif isinstance(value, Expression):
            return is_expression_constant(value)
    else:
        raise NotImplementedError("Not expecting a non analog lane here.")


def is_expression_constant(expression: Expression) -> bool:
    return "t" not in expression.upstream_variables
