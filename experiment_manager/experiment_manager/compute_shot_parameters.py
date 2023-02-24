from copy import copy
from typing import Any, TypedDict, Iterable

import numpy
import numpy as np

from device_config.channel_config import ChannelSpecialPurpose
from experiment.configuration import ExperimentConfig
from expression import Expression
from ni6738_analog_card.configuration import NI6738SequencerConfiguration
from sequence.configuration import ShotConfiguration, CameraLane, Ramp, AnalogLane
from spincore_sequencer.configuration import SpincoreSequencerConfiguration
from spincore_sequencer.runtime import (
    Instruction,
    Continue,
    Loop,
    Stop,
)
from units import ureg, Quantity, units, DimensionalityError, dimensionless
from variable import VariableNamespace


def compute_shot_parameters(
    experiment_config: ExperimentConfig,
    shot_config: ShotConfiguration,
    variables: VariableNamespace,
) -> dict[str, dict[str, Any]]:
    """Compute the parameters to be applied to the devices before a shot"""

    result = {}

    step_durations = evaluate_step_durations(shot_config, variables)
    verify_step_durations(experiment_config, step_durations, shot_config)
    camera_instructions = compute_camera_instructions(step_durations, shot_config)
    result |= get_camera_parameters(camera_instructions)

    analog_times = evaluate_analog_local_times(
        shot_config,
        step_durations,
        get_analog_timestep(experiment_config),
        get_digital_time_step(experiment_config),
    )

    camera_triggers = {
        camera_name: instructions["triggers"]
        for camera_name, instructions in camera_instructions.items()
    }
    spincore_instructions = generate_digital_instructions(
        shot_config,
        step_durations,
        analog_times,
        camera_triggers,
        experiment_config.spincore_config,
        get_analog_timestep(experiment_config),
    )
    result[experiment_config.spincore_config.device_name] = {
        "instructions": spincore_instructions
    }

    analog_values = evaluate_analog_values(shot_config, analog_times, variables)
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
        duration = Quantity(expression.evaluate(context | units))
        try:
            durations.append(duration.to("s").magnitude)
        except DimensionalityError as err:
            err.extra_msg = f" for the duration ({expression.body}) of step '{name}'"
            raise err
    return durations


def verify_step_durations(
    experiment_config: ExperimentConfig,
    step_durations: list[float],
    shot_config: ShotConfiguration,
) -> None:
    min_timestep = get_minimum_allowed_timestep(experiment_config)
    for step_name, duration in zip(shot_config.step_names, step_durations):
        if duration < min_timestep:
            raise TimingError(
                f"Duration of step '{step_name}' ({(duration * ureg.s).to('ns')})"
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
    step_durations: list[float], shot: ShotConfiguration
) -> dict[str, "CameraInstructions"]:
    """Compute the parameters to be applied to each camera"""

    result = {}
    camera_lanes = shot.get_lanes(CameraLane)
    shot_duration = sum(step_durations)
    for camera_name, camera_lane in camera_lanes.items():
        triggers = [False] * len(step_durations)
        exposures = []
        for _, start, stop in camera_lane.get_picture_spans():
            triggers[start:stop] = [True] * (stop - start)
            exposures.append(sum(step_durations[start:stop]))
        instructions: CameraInstructions = {
            "timeout": shot_duration + 1,  # add a second to be safe
            "triggers": triggers,
            "exposures": exposures,
        }
        result[camera_name] = instructions
    return result


class CameraInstructions(TypedDict):
    """Instruction to take picture for a camera

    Attributes:
        timeout: Maximum time to wait for the camera to take the picture
        exposures: Duration of each exposure in s
        triggers: Whether to camera trigger should be up or down at each step
    """

    timeout: float
    exposures: list[float]
    triggers: list[bool]


def get_camera_parameters(
    camera_instructions: dict[str, CameraInstructions]
) -> dict[str, dict[str, Any]]:
    result = {}

    for camera, instructions in camera_instructions.items():
        result[camera] = dict(
            timeout=instructions["timeout"], exposures=instructions["exposures"]
        )

    return result


def evaluate_analog_local_times(
    shot: ShotConfiguration,
    step_durations: list[float],
    analog_time_step: float,
    digital_time_step: float,
) -> list[numpy.ndarray]:
    """Compute new time points within each step to evaluate analog ramps"""

    analog_times = []
    last_analog_time = -numpy.inf
    for step, duration in enumerate(step_durations):
        is_step_of_constants = all(
            _is_constant(lane.get_effective_value(step)) for lane in shot.analog_lanes
        )
        start = max(last_analog_time + analog_time_step, digital_time_step)
        stop = duration - analog_time_step
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
        last_analog_time -= duration
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
    step_durations: list[float],
    analog_times: list[numpy.ndarray],
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
    for step in range(len(step_durations)):
        values = [False] * spincore_config.number_channels
        for camera, triggers in camera_triggers.items():
            values[camera_channels[camera]] = triggers[step]
        for lane in shot.digital_lanes:
            channel = spincore_config.get_channel_index(lane.name)
            values[channel] = lane.get_effective_value(step)
        if len(analog_times[step]) > 0:
            duration = analog_times[step][0]
        else:
            duration = step_durations[step]
        instructions.append(Continue(values=values, duration=duration))
        if len(analog_times[step]) > 0:
            (low_values := copy(values))[analog_clock_channel] = False
            (high_values := copy(low_values))[analog_clock_channel] = True
            instructions.append(
                Loop(
                    repetitions=len(analog_times[step]),
                    start_values=high_values,
                    start_duration=analog_time_step / 2,
                    end_values=low_values,
                    end_duration=analog_time_step / 2,
                )
            )
            instructions.append(
                Continue(
                    values=low_values,
                    duration=step_durations[step]
                    - (analog_times[step][-1] + analog_time_step),
                )
            )
    instructions.append(Stop(values=values))
    return instructions


def evaluate_analog_values(
    shot: ShotConfiguration,
    analog_times: list[numpy.ndarray],
    context: VariableNamespace,
) -> dict[str, Quantity]:
    """Computes the analog values of each lane, in lane units"""

    result = {}
    for lane in shot.analog_lanes:
        lane_values = evaluate_lane_values(shot.step_names, lane, analog_times, context)
        result[lane.name] = numpy.concatenate(lane_values) * Quantity(
            1, units=lane.units
        )
    return result


def evaluate_lane_values(
    step_names: list[str],
    lane: AnalogLane,
    analog_times: list[np.ndarray],
    context: VariableNamespace,
) -> list[np.ndarray]:
    # Assume that analog_times have unwrapped times
    values = evaluate_lane_expressions(step_names, lane, analog_times, context)

    return [values[step] for step in range(len(analog_times))]


def evaluate_lane_expressions(
    step_names: list[str],
    lane: AnalogLane,
    analog_times: list[np.ndarray],
    context: VariableNamespace,
) -> dict[int, np.ndarray]:
    result = {}

    for step_index, step_name in enumerate(step_names):
        cell_value = lane.get_effective_value(step_index)
        if isinstance(cell_value, Expression):
            values = evaluate_expression(
                cell_value, analog_times[step_index], context, step_name, lane.name
            )

            if values.is_compatible_with(dimensionless) and lane.has_dimension():
                values = Quantity(values.to(dimensionless).magnitude, units=lane.units)
            else:
                values = values.to(lane.units)
            result[step_index] = values.magnitude
    return result


def evaluate_expression(
    expression: Expression,
    times: np.ndarray,
    context: VariableNamespace,
    step_name: str,
    lane_name: str,
) -> Quantity:
    if _is_constant(expression):
        try:
            value = Quantity(expression.evaluate(context | units))
        except NameError as err:
            raise NameError(
                f"'{err.name}' is not defined in expression '{expression.body}' "
                f"(step: {step_name}, lane: {lane_name})"
            )
        return numpy.full_like(times, value.magnitude) * value.units
    else:
        try:
            value = Quantity(
                expression.evaluate(context | units | {"t": times * ureg.s})
            )
        except NameError as err:
            raise NameError(
                f"'{err.name}' is no defined in expression '{expression.body}' "
                f"(step: {step_name}, lane: {lane_name})"
            )
        return value


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
