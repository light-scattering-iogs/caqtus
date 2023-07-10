import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from device.configuration import DeviceName
from experiment.configuration import (
    ExperimentConfig,
    DeviceParameter,
)
from sequence.configuration import (
    ShotConfiguration,
    CameraLane,
    TakePicture,
)
from sequencer.channel import ChannelInstruction
from sequencer.configuration import SequencerConfiguration
from sequencer.instructions import ChannelLabel
from variable.namespace import VariableNamespace
from .camera_instruction import CameraInstruction
from .clock_instruction import ClockInstruction, ClockStepInstruction
from .compile_lane import (
    compile_lane,
    empty_channel_instruction,
    get_step_bounds,
    compile_camera_instruction,
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

    # steps.analog_times = evaluate_analog_local_times(
    #     shot_config,
    #     steps,
    #     get_analog_timestep(experiment_config),
    #     get_digital_time_step(experiment_config),
    # )
    #
    # camera_triggers = {
    #     camera_name: instructions.triggers
    #     for camera_name, instructions in camera_instructions.items()
    # }
    # spincore_name, spincore_config = get_spincore(experiment_config)
    # spincore_instructions = generate_digital_instructions(
    #     shot_config,
    #     steps,
    #     camera_triggers,
    #     spincore_config,
    #     get_analog_timestep(experiment_config),
    # )
    # result[spincore_name] = {"instructions": spincore_instructions}
    #
    # ni6738_name, ni6738_config = get_ni6738(experiment_config)
    # analog_values = evaluate_analog_values(shot_config, steps, variables)
    # analog_voltages = generate_analog_voltages(ni6738_config, analog_values)
    # result[ni6738_name] = {"values": analog_voltages}
    #
    # if extra:
    #     result["extra"] = {
    #         "steps": steps,
    #         "analog_values": analog_values,
    #         "camera_instructions": camera_instructions,
    #     }
    # return result


def compile_sequencer_instructions(
    sequencer_config: SequencerConfiguration,
    shot_config: ShotConfiguration,
    variables: VariableNamespace,
    camera_instructions: Mapping[DeviceName, CameraInstruction],
    clock_requirements: dict[DeviceName, Sequence[ClockInstruction]],
) -> dict[ChannelLabel, ChannelInstruction[bool]]:
    step_durations = compile_step_durations(
        shot_config.step_names, shot_config.step_durations, variables
    )
    instructions: dict[ChannelLabel, ChannelInstruction[bool]] = {}

    for channel_number, channel in enumerate(sequencer_config.channels):
        if channel.has_special_purpose():
            target = str(channel.description)
            if target in camera_instructions:
                instruction = compile_camera_instruction(
                    camera_instructions[target], sequencer_config.time_step
                )
            elif target in clock_requirements:
                instruction = compile_clock_instruction(
                    clock_requirements[target], sequencer_config.time_step
                )
            else:
                raise NotImplementedError
        else:
            if lane := shot_config.find_lane(channel.description):
                instruction = compile_lane(
                    lane, step_durations, sequencer_config.time_step, variables
                )
            else:
                instruction = empty_channel_instruction(
                    channel.default_value, step_durations, sequencer_config.time_step
                )
        instructions[ChannelLabel(channel_number)] = instruction
    return instructions


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

    step_bounds = get_step_bounds(step_durations)

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
            triggers.append((state, step_bounds[start], step_bounds[stop]))
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
        exposures = [stop - start for _, start, stop in instruction.triggers]
        result[camera] = dict(timeout=instruction.timeout, exposures=exposures)

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
    step_bounds = get_step_bounds(step_durations)

    sequencer = DeviceName("NI6738 card")
    sequencer_config = sequencer_configs[sequencer]
    clock_instructions = []
    for step_index, duration in enumerate(step_durations):
        if is_step_of_constant(step_index, sequencer):
            clock_type = ClockStepInstruction.TriggerStart
        else:
            clock_type = ClockStepInstruction.Clock
        clock_instructions.append(
            ClockInstruction(
                start=step_bounds[step_index],
                stop=step_bounds[step_index + 1],
                time_step=sequencer_config.time_step,
                order=clock_type,
            )
        )
    return {sequencer: clock_instructions}
