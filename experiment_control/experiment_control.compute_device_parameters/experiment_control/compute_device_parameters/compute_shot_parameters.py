import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Iterable, Optional

import numpy as np
from device.configuration.channel_config import (
    ChannelSpecialPurpose,
)

from device.configuration import DeviceName
from experiment.configuration import (
    ExperimentConfig,
    DeviceParameter,
    SpincoreSequencerConfiguration,
)
from sequence.configuration import (
    ShotConfiguration,
    CameraLane,
)
from sequencer.channel import ChannelInstruction
from sequencer.configuration import SequencerConfiguration
from sequencer.instructions import ChannelLabel
from variable.namespace import VariableNamespace
from .compile_lane import compile_lane
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

    sequencer_configs = experiment_config.get_device_configs(SequencerConfiguration)
    sequencer_instructions = {
        sequencer_name: instructions
        for sequencer_name, config in sequencer_configs.items()
        if (
            instructions := compile_sequencer_instructions(
                config, shot_config, variables
            )
        )
    }

    camera_instructions = compute_camera_instructions(steps, shot_config)
    result |= get_camera_parameters(camera_instructions)

    steps.analog_times = evaluate_analog_local_times(
        shot_config,
        steps,
        get_analog_timestep(experiment_config),
        get_digital_time_step(experiment_config),
    )

    camera_triggers = {
        camera_name: instructions.triggers
        for camera_name, instructions in camera_instructions.items()
    }
    spincore_name, spincore_config = get_spincore(experiment_config)
    spincore_instructions = generate_digital_instructions(
        shot_config,
        steps,
        camera_triggers,
        spincore_config,
        get_analog_timestep(experiment_config),
    )
    result[spincore_name] = {"instructions": spincore_instructions}

    ni6738_name, ni6738_config = get_ni6738(experiment_config)
    analog_values = evaluate_analog_values(shot_config, steps, variables)
    analog_voltages = generate_analog_voltages(ni6738_config, analog_values)
    result[ni6738_name] = {"values": analog_voltages}

    if extra:
        result["extra"] = {
            "steps": steps,
            "analog_values": analog_values,
            "camera_instructions": camera_instructions,
        }
    return result


def compile_sequencer_instructions(
    sequencer_config: SequencerConfiguration,
    shot_config: ShotConfiguration,
    variables: VariableNamespace,
) -> dict[ChannelLabel, ChannelInstruction[bool]]:
    step_durations = compile_step_durations(
        shot_config.step_names, shot_config.step_durations, variables
    )
    instructions: dict[ChannelLabel, ChannelInstruction[bool]] = {}

    for channel_number, channel in enumerate(sequencer_config.channels):
        if not channel.has_special_purpose():
            if lane := shot_config.find_lane(channel.description):
                logical_instruction = compile_lane(
                    lane, step_durations, sequencer_config.time_step, variables
                )
                raw_instruction = logical_instruction.apply(
                    channel.output_mapping.convert
                )
                instructions[ChannelLabel(channel_number)] = raw_instruction
    return instructions


def compute_camera_instructions(
    steps: tuple[StepProperties, ...], shot: ShotConfiguration
) -> dict[DeviceName, "CameraInstructions"]:
    """Compute the parameters to be applied to each camera

    Returns:
        A dictionary mapping camera names to their parameters
    """

    result = {}
    shot_duration = sum(step.duration for step in steps)

    camera_lanes = shot.get_lanes(CameraLane)
    for lane_name, lane in camera_lanes.items():
        triggers = [False] * len(steps)
        exposures = []
        for _, start, stop in lane.get_picture_spans():
            triggers[start:stop] = [True] * (stop - start)
            picture_duration = sum(step.duration for step in steps[start:stop])
            exposures.append(picture_duration)
        instructions = CameraInstructions(
            timeout=shot_duration
            + 1,  # add a second to be safe and not timeout too early if the shot takes time to start
            triggers=triggers,
            exposures=exposures,
        )
        result[DeviceName(lane_name)] = instructions
    return result


@dataclass(frozen=True)
class CameraInstructions:
    """Instruction to take pictures for a camera

    fields:
        timeout: Maximum time to wait for the camera to take the picture
        exposures: Duration of each exposure in seconds. The length of this list should be the same as the number of
        pictures.
        triggers: Whether to camera trigger should be up or down at each step. The length of this list should be the
        same as the number of steps.
    """

    timeout: float
    exposures: list[float]
    triggers: list[bool]


def get_camera_parameters(
    camera_instructions: Mapping[DeviceName, CameraInstructions]
) -> dict[DeviceName, dict[DeviceParameter, Any]]:
    """Extract the parameters to be applied to each camera from the instructions.

    This function only keeps the parameters to be applied to a camera. It removes the triggers because they will be used
    to program a digital sequencer and not the cameras themselves.

    Returns:
        A dictionary mapping camera names to their parameters
    """

    result = {}

    for camera, instructions in camera_instructions.items():
        result[camera] = dict(
            timeout=instructions.timeout, exposures=instructions.exposures
        )

    return result


def get_camera_channels(
    spincore_config: SpincoreSequencerConfiguration, camera_names: Iterable[str]
) -> dict[str, int]:
    return {
        name: spincore_config.get_channel_index(ChannelSpecialPurpose(purpose=name))
        for name in camera_names
    }
