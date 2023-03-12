from collections import namedtuple
from copy import copy
from typing import Any, TypedDict, Iterable, Optional

import numpy
import numpy as np

from device_config.channel_config import ChannelSpecialPurpose
from experiment.configuration import ExperimentConfig
from expression import Expression
from ni6738_analog_card.configuration import NI6738SequencerConfiguration
from sequence.configuration import (
    ShotConfiguration,
    CameraLane,
    Ramp,
    AnalogLane,
    LinearRamp,
)
from spincore_sequencer.configuration import SpincoreSequencerConfiguration
from spincore_sequencer.runtime import (
    Instruction,
    Continue,
    Loop,
    Stop,
)
from units import ureg, Quantity, units, dimensionless
from variable import VariableNamespace

StepProperties = namedtuple("StepProperties", ["name", "duration", "analog_times"])


class RuntimeSteps:
    def __init__(self, names: list[str]):
        self.names = names
        self.durations: Optional[list[float]] = None
        self.analog_times: Optional[list[np.ndarray]] = None

    def __len__(self) -> int:
        return len(self.names)

    def __iter__(self) -> Iterable[StepProperties]:
        if self.durations is None:
            durations = [None] * len(self)
        else:
            durations = self.durations
        if self.analog_times is None:
            analog_times = [None] * len(self)
        else:
            analog_times = self.analog_times
        return iter(
            StepProperties(name, duration, analog_times)
            for name, duration, analog_times in zip(self.names, durations, analog_times)
        )


def compute_shot_parameters(
    experiment_config: ExperimentConfig,
    shot_config: ShotConfiguration,
    variables: VariableNamespace,
) -> dict[str, dict[str, Any]]:
    """Compute the parameters to be applied to the devices before a shot"""

    result = {}

    steps = RuntimeSteps(names=shot_config.step_names)

    steps.durations = evaluate_step_durations(shot_config, variables)
    verify_step_durations(experiment_config, steps)
    camera_instructions = compute_camera_instructions(steps, shot_config)
    result |= get_camera_parameters(camera_instructions)

    steps.analog_times = evaluate_analog_local_times(
        shot_config,
        steps,
        get_analog_timestep(experiment_config),
        get_digital_time_step(experiment_config),
    )

    camera_triggers = {
        camera_name: instructions["triggers"]
        for camera_name, instructions in camera_instructions.items()
    }
    spincore_instructions = generate_digital_instructions(
        shot_config,
        steps,
        camera_triggers,
        experiment_config.spincore_config,
        get_analog_timestep(experiment_config),
    )
    result[experiment_config.spincore_config.device_name] = {
        "instructions": spincore_instructions
    }

    analog_values = evaluate_analog_values(shot_config, steps, variables)
    analog_voltages = generate_analog_voltages(experiment_config, analog_values)
    result[experiment_config.ni6738_config.device_name] = {"values": analog_voltages}
    return result


def evaluate_step_durations(
    shot: ShotConfiguration, context: VariableNamespace
) -> list[float]:
    """Compute the duration of each step in the shot

    This function evaluates all the step duration expressions by replacing the variables with their numerical values
    provided in 'context'. It returns a list of all step durations in seconds.
    """

    durations = []
    for name, expression in zip(shot.step_names, shot.step_durations):
        try:
            duration = expression.evaluate(context | units)
        except Exception as error:
            raise ValueError(
                f"Error evaluating duration '{expression.body}' of step '{name}'"
            ) from error
        try:
            seconds = duration.to("s").magnitude
        except Exception as error:
            raise ValueError(
                f"Duration '{expression.body}' of step '{name}' is not a duration (got {duration})"
            ) from error
        durations.append(seconds)
    return durations


def verify_step_durations(
    experiment_config: ExperimentConfig,
    steps: RuntimeSteps,
) -> None:
    min_timestep = get_minimum_allowed_timestep(experiment_config)
    for step in steps:
        if step.duration < min_timestep:
            raise TimingError(
                f"Duration of step '{step.name}' ({(step.duration * ureg.s).to('ns')})"
                " is too short"
            )


def get_minimum_allowed_timestep(
    experiment_config: ExperimentConfig,
) -> float:
    return max(
        config.time_step
        for config in experiment_config.get_device_configs(
            SpincoreSequencerConfiguration
        ).values()
    )


class TimingError(ValueError):
    pass


def compute_camera_instructions(
    steps: RuntimeSteps, shot: ShotConfiguration
) -> dict[str, "CameraInstructions"]:
    """Compute the parameters to be applied to each camera

    Returns:
        A dictionary mapping camera names to their parameters
    """

    result = {}
    camera_lanes = shot.get_lanes(CameraLane)
    shot_duration = sum(step.duration for step in steps)
    for camera_name, camera_lane in camera_lanes.items():
        triggers = [False] * len(steps)
        exposures = []
        for _, start, stop in camera_lane.get_picture_spans():
            triggers[start:stop] = [True] * (stop - start)
            exposures.append(sum(steps.durations[start:stop]))
        instructions = CameraInstructions(
            timeout=shot_duration
            + 1,  # add a second to be safe and not timeout too early if the shot starts late
            triggers=triggers,
            exposures=exposures,
        )
        result[camera_name] = instructions
    return result


class CameraInstructions(TypedDict):
    """Instruction to take pictures for a camera

    Attributes:
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
    camera_instructions: dict[str, CameraInstructions]
) -> dict[str, dict[str, Any]]:
    """Extract the parameters to be applied to each camera from the instructions

    This function only keeps the parameters to be applied to a camera. It removes the triggers because they will be used
    to program a digital sequencer and not the cameras themselves.

    Returns:
        A dictionary mapping camera names to their parameters
    """

    result = {}

    for camera, instructions in camera_instructions.items():
        result[camera] = dict(
            timeout=instructions["timeout"], exposures=instructions["exposures"]
        )

    return result


def evaluate_analog_local_times(
    shot: ShotConfiguration,
    steps: RuntimeSteps,
    analog_time_step: float,
    digital_time_step: float,
) -> list[numpy.ndarray]:
    """Compute new time points within each step to evaluate analog ramps"""

    analog_times = []
    last_analog_time = -numpy.inf
    for step_index, step in enumerate(steps):
        is_step_of_constants = all(
            _is_constant(lane.get_effective_value(step_index))
            for lane in shot.analog_lanes
        )
        start = max(last_analog_time + analog_time_step, digital_time_step)
        stop = step.duration - analog_time_step
        if is_step_of_constants:
            if stop > start + analog_time_step:
                step_analog_times = numpy.array([start])
            else:
                step_analog_times = numpy.array([])
        else:
            step_analog_times = numpy.arange(
                start,
                stop,
                analog_time_step,
            )
        if len(step_analog_times) > 0:
            last_analog_time = step_analog_times[-1]
        last_analog_time -= step.duration
        analog_times.append(step_analog_times)
    return analog_times


def _is_constant(value: Expression | Ramp) -> bool:
    if isinstance(value, Ramp):
        return False
    elif isinstance(value, Expression):
        return _is_constant_expression(value)
    else:
        raise TypeError(f"Unexpected type {type(value)}")


def _is_constant_expression(expression: Expression) -> bool:
    return "t" not in expression.upstream_variables


def get_analog_timestep(experiment_config: ExperimentConfig) -> float:
    ni6738_configs = list(
        experiment_config.get_device_configs(NI6738SequencerConfiguration).values()
    )
    if len(ni6738_configs) == 0:
        raise ValueError("No NI6738 sequencer configuration found")
    if len(ni6738_configs) > 1:
        raise ValueError("Multiple NI6738 sequencer configurations found")
    return ni6738_configs[0].time_step


def get_digital_time_step(experiment_config: ExperimentConfig) -> float:
    spincore_configs = list(
        experiment_config.get_device_configs(SpincoreSequencerConfiguration).values()
    )
    if len(spincore_configs) == 0:
        raise ValueError("No Spincore sequencer configuration found")
    if len(spincore_configs) > 1:
        raise ValueError("Multiple Spincore sequencer configurations found")
    return spincore_configs[0].time_step


def generate_digital_instructions(
    shot: ShotConfiguration,
    steps: RuntimeSteps,
    camera_triggers: dict[str, list[bool]],
    spincore_config: SpincoreSequencerConfiguration,
    analog_time_step: float,
) -> list[Instruction]:
    instructions = []
    # noinspection PyTypeChecker
    analog_clock_channel = spincore_config.get_channel_index(
        ChannelSpecialPurpose(purpose="NI6738 analog sequencer")
    )
    camera_channels = get_camera_channels(spincore_config, camera_triggers.keys())
    values = [False] * spincore_config.number_channels
    for step_index, step in enumerate(steps):
        values = [False] * spincore_config.number_channels
        for camera, triggers in camera_triggers.items():
            values[camera_channels[camera]] = triggers[step_index]
        for lane in shot.digital_lanes:
            channel = spincore_config.get_channel_index(lane.name)
            values[channel] = lane.get_effective_value(step_index)
        if len(step.analog_times) > 0:
            duration = step.analog_times[0]
        else:
            duration = step.duration
        instructions.append(Continue(values=values, duration=duration))
        if len(step.analog_times) > 0:
            (low_values := copy(values))[analog_clock_channel] = False
            (high_values := copy(low_values))[analog_clock_channel] = True
            instructions.append(
                Loop(
                    repetitions=len(step.analog_times),
                    start_values=high_values,
                    start_duration=analog_time_step / 2,
                    end_values=low_values,
                    end_duration=analog_time_step / 2,
                )
            )
            instructions.append(
                Continue(
                    values=low_values,
                    duration=step.duration - (step.analog_times[-1] + analog_time_step),
                )
            )
    instructions.append(Stop(values=values))
    return instructions


def evaluate_analog_values(
    shot: ShotConfiguration,
    steps: RuntimeSteps,
    context: VariableNamespace,
) -> dict[str, Quantity]:
    """Computes the analog values of each lane, in lane units"""

    result = {}
    for lane in shot.analog_lanes:
        lane_values = evaluate_lane_values(steps, lane, context)
        result[lane.name] = numpy.concatenate(lane_values) * Quantity(
            1, units=lane.units
        )
    return result


def evaluate_lane_values(
    steps: RuntimeSteps,
    lane: AnalogLane,
    context: VariableNamespace,
) -> list[np.ndarray]:
    # Assume that analog_times have unwrapped times
    values = evaluate_lane_expressions(steps, lane, context)

    return values


def evaluate_lane_expressions(
    steps: RuntimeSteps,
    lane: AnalogLane,
    context: VariableNamespace,
) -> list[np.ndarray]:
    result = []

    for step_index, step in enumerate(steps):
        cell_value = lane.get_effective_value(step_index)
        if isinstance(cell_value, Expression):
            try:
                values = evaluate_expression(
                    cell_value, step.analog_times, context, lane
                )
            except Exception as error:
                raise RuntimeError(
                    f"Cannot evaluate expression '{cell_value.body}' for step '{step.name}' in lane '{lane.name}'"
                ) from error
            result.append(values.magnitude)
        else:
            raise TypeError(f"Unexpected type {type(cell_value)}")
    return result


def evaluate_expression(
    expression: Expression,
    times: np.ndarray,
    context: VariableNamespace,
    lane: AnalogLane,
) -> Quantity:
    if _is_constant(expression):
        value = expression.evaluate(context | units)
        values = numpy.full_like(times, value.magnitude) * value.units
    else:
        values = expression.evaluate(context | units | {"t": times * ureg.s})

    if values.is_compatible_with(dimensionless) and lane.has_dimension():
        values = Quantity(values.to(dimensionless).magnitude, units=lane.units)
    else:
        values = values.to(lane.units)
    return values


def generate_analog_voltages(
    experiment_config: ExperimentConfig, analog_values: dict[str, Quantity]
):
    """Converts the analog values in lane units to voltages"""

    data_length = 0
    for array in analog_values.values():
        data_length = len(array)
        break
    data = numpy.zeros(
        (NI6738SequencerConfiguration.number_channels, data_length), dtype=numpy.float64
    )

    for name, values in analog_values.items():
        voltages = (
            experiment_config.ni6738_config.convert_to_output_units(name, values)
            .to("V")
            .magnitude
        )
        channel_number = experiment_config.ni6738_config.get_channel_index(name)
        data[channel_number] = voltages
    return data


def get_camera_channels(
    spincore_config: SpincoreSequencerConfiguration, camera_names: Iterable[str]
) -> dict[str, int]:
    return {
        name: spincore_config.get_channel_index(ChannelSpecialPurpose(purpose=name))
        for name in camera_names
    }
