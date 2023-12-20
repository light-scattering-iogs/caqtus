import logging
import math
from collections.abc import Sequence, Mapping
from dataclasses import dataclass
from numbers import Real

import numpy as np

from core.configuration import Expression, DottedVariableName
from core.configuration.lane import Lane, AnalogLane, Ramp, DigitalLane, Blink
from core.types import Parameter, is_analog_value
from core.types.units import Quantity, ureg, units, dimensionless, magnitude_in_unit
from sequencer.channel.channel_instructions import ChannelType
from sequencer.instructions.struct_array_instruction import (
    SequencerInstruction,
    Pattern,
)
from .camera_instruction import CameraInstruction
from .evaluation_error import ShotEvaluationError
from .timing import get_step_starts, start_tick, stop_tick, number_ticks
from ..variable_namespace import VariableNamespace

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ns = 1e-9


def empty_channel_instruction(
    default_value: ChannelType, step_durations: Sequence[float], time_step: int
) -> SequencerInstruction[ChannelType]:
    duration = sum(step_durations)
    length = number_ticks(0.0, duration, time_step * ns)
    return Pattern([default_value]) * length


def compile_lane(
    lane: Lane,
    step_durations: Sequence[float],
    time_step: int,
    variables: VariableNamespace,
) -> SequencerInstruction:
    if isinstance(lane, DigitalLane):
        return compile_digital_lane(step_durations, lane, variables, time_step)
    elif isinstance(lane, AnalogLane):
        return compile_analog_lane(step_durations, lane, variables, time_step)
    else:
        raise NotImplementedError(f"Unknown lane type {type(lane)}")


def compile_digital_lane(
    step_durations: Sequence[float],
    lane: DigitalLane,
    variables: VariableNamespace,
    time_step: int,
) -> SequencerInstruction[bool]:
    step_bounds = get_step_starts(step_durations)
    instructions = []
    for cell_value, start, stop in lane.get_value_spans():
        length = number_ticks(step_bounds[start], step_bounds[stop], time_step * ns)
        if isinstance(cell_value, bool):
            instructions.append(Pattern([cell_value]) * length)
        elif isinstance(cell_value, Blink):
            period = cell_value.period.evaluate(variables | units).to("ns").magnitude
            duty_cycle = (
                Quantity(cell_value.duty_cycle.evaluate(variables | units))
                .to(dimensionless)
                .magnitude
            )
            if not 0 <= duty_cycle <= 1:
                raise ShotEvaluationError(
                    f"Duty cycle '{cell_value.duty_cycle.body}' must be between 0 and 1, not {duty_cycle}"
                )
            num_ticks_per_period, _ = divmod(period, time_step)
            num_ticks_high = math.ceil(num_ticks_per_period * duty_cycle)
            num_ticks_low = num_ticks_per_period - num_ticks_high
            num_clock_pulses, remainder = divmod(length, num_ticks_per_period)
            phase = (
                Quantity(cell_value.phase.evaluate(variables | units))
                .to(dimensionless)
                .magnitude
            )
            if not 0 <= phase <= 2 * math.pi:
                raise ShotEvaluationError(
                    f"Phase '{cell_value.phase.body}' must be between 0 and 2*pi, not {phase}"
                )
            split_position = round(phase / (2 * math.pi) * num_ticks_per_period)
            clock_pattern = (
                Pattern([True]) * num_ticks_high + Pattern([False]) * num_ticks_low
            )
            a, b = clock_pattern[:split_position], clock_pattern[split_position:]
            clock_pattern = b + a
            pattern = clock_pattern * num_clock_pulses + Pattern([False]) * remainder
            if not len(pattern) == length:
                raise RuntimeError(
                    f"Pattern length {len(pattern)} does not match expected length {length}"
                )
            print(f"{pattern=}")
            instructions.append(pattern)
        else:
            raise NotImplementedError(f"Unexpected value {cell_value} in digital lane")
    return SequencerInstruction.join(*instructions)


def compile_analog_lane(
    step_durations: Sequence[float],
    lane: AnalogLane,
    variables: VariableNamespace,
    time_step: int,
) -> SequencerInstruction[float]:
    return CompileAnalogLane(step_durations, lane, variables, time_step).compile()


@dataclass(slots=True)
class CompileAnalogLane:
    step_durations: Sequence[float]
    lane: AnalogLane
    variables: VariableNamespace
    time_step: int

    def compile(self) -> SequencerInstruction[float]:
        step_starts = get_step_starts(self.step_durations)
        instructions = []
        for (
            cell_value,
            cell_start_index,
            cell_stop_index,
        ) in self.lane.get_value_spans():
            cell_start_time = step_starts[cell_start_index]
            cell_stop_time = step_starts[cell_stop_index]
            if isinstance(cell_value, Expression):
                instruction = self._compile_expression_cell(
                    cell_value, cell_start_time, cell_stop_time
                )
            elif isinstance(cell_value, Ramp):
                instruction = self._compile_ramp_cell(cell_start_index)
            else:
                raise NotImplementedError(f"Unknown cell type {type(cell_value)}")

            for step_index in range(cell_start_index, cell_stop_index):
                step_start_tick = start_tick(
                    step_starts[step_index], self.time_step * ns
                )
                step_stop_tick = stop_tick(
                    step_starts[step_index + 1], self.time_step * ns
                )
                split_index = step_stop_tick - step_start_tick
                left = instruction[:split_index]
                instructions.append(left)
                instruction = instruction[split_index:]
        return SequencerInstruction.join(*instructions)

    def _compile_expression_cell(
        self, expression: Expression, start: float, stop: float
    ) -> SequencerInstruction[float]:
        variables = self.variables | units
        length = number_ticks(start, stop, self.time_step * ns)
        if _is_constant(expression):
            value = self._evaluate_expression(expression, variables)
            result = Pattern([float(value)]) * length
        else:
            variables = variables | {
                DottedVariableName("t"): (
                    _compute_time_array(start, stop, self.time_step) - start
                )
                * ureg.s
            }
            result = Pattern(self._evaluate_expression(expression, variables))
        if not len(result) == length:
            raise ShotEvaluationError(
                f"Expression '{expression}' evaluates to an array of length"
                f" {len(result)} while the expected length is {length}"
            )
        return result

    def _compile_ramp_cell(self, start_index: int) -> SequencerInstruction[float]:
        stop_index = self.lane.end_index(start_index)
        step_bounds = get_step_starts(self.step_durations)
        t0 = step_bounds[start_index]
        t1 = step_bounds[stop_index]
        previous_step_duration = (
            step_bounds[self.lane.end_index(start_index - 1)]
            - step_bounds[self.lane.start_index(start_index - 1)]
        )
        variables = (
            self.variables
            | units
            | {DottedVariableName("t"): previous_step_duration * ureg.s}
        )
        previous_value = self._evaluate_expression(
            self.lane.get_effective_value(start_index - 1), variables
        )

        variables = self.variables | units | {DottedVariableName("t"): 0.0 * ureg.s}
        next_value = self._evaluate_expression(
            self.lane.get_effective_value(stop_index), variables
        )

        if self.lane.units == "dB":
            previous_value = 10 ** (previous_value / 10)
            next_value = 10 ** (next_value / 10)

        t = _compute_time_array(t0, t1, self.time_step)
        result = (t - t0) / (t1 - t0) * (next_value - previous_value) + previous_value

        if self.lane.units == "dB":
            if np.any(np.isnan(result)):
                raise ShotEvaluationError(
                    f"Ramp cell from {previous_value} to {next_value} contains NaNs"
                )
            result = 10 * np.log10(result)
        return Pattern(result)

    def _evaluate_expression(
        self, expression: Expression, variables: Mapping[DottedVariableName, Parameter]
    ) -> Real | np.ndarray:
        try:
            value = expression.evaluate(variables | units)
        except Exception as e:
            raise ShotEvaluationError(
                f"Could not evaluate expression '{expression.body}'"
            ) from e
        if not is_analog_value(value):
            raise ShotEvaluationError(
                f"Expression '{expression.body}' evaluates to a non-analog value"
                f" ({value})"
            )
        return self._convert_to_lane_units(value)

    def _convert_to_lane_units(self, value: Quantity) -> Real | np.ndarray:
        return magnitude_in_unit(value, self.lane.units)


def _is_constant(expression: Expression) -> bool:
    return "t" not in expression.upstream_variables


def _compute_time_array(start: float, stop: float, time_step: int) -> np.ndarray:
    times = (
        np.arange(start_tick(start, time_step * ns), stop_tick(stop, time_step * ns))
        * time_step
        * ns
    )
    return times


def compile_camera_instruction(
    camera_instruction: CameraInstruction,
    time_step: int,
) -> SequencerInstruction[bool]:
    instructions = []
    for value, start, stop, _ in camera_instruction.triggers:
        length = number_ticks(start, stop, time_step * ns)
        instructions.append(Pattern([value]) * length)
    return SequencerInstruction.join(*instructions)
