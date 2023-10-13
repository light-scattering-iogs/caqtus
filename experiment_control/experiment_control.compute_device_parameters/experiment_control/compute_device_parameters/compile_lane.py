import logging
import math
from collections.abc import Sequence, Mapping
from dataclasses import dataclass
from numbers import Real

import numpy as np

from analog_lane.configuration import AnalogLane, Ramp
from digital_lane.configuration import DigitalLane, Blink
from expression import Expression
from lane.configuration import Lane
from parameter_types import is_analog_value, Parameter
from parameter_types.analog_value import magnitude_in_unit
from sequencer.channel import ChannelInstruction, ChannelPattern
from sequencer.channel.channel_instructions import ChannelType
from units import Quantity, ureg, units, dimensionless
from variable.name import DottedVariableName
from variable.namespace import VariableNamespace
from .camera_instruction import CameraInstruction
from .clock_instruction import ClockInstruction
from .evaluation_error import ShotEvaluationError
from .timing import get_step_starts, start_tick, stop_tick, number_ticks

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ns = 1e-9


def empty_channel_instruction(
    default_value: ChannelType, step_durations: Sequence[float], time_step: int
) -> ChannelInstruction[ChannelType]:
    duration = sum(step_durations)
    length = number_ticks(0.0, duration, time_step * ns)
    return ChannelPattern([default_value]) * length


def compile_lane(
    lane: Lane,
    step_durations: Sequence[float],
    time_step: int,
    variables: VariableNamespace,
) -> ChannelInstruction:
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
) -> ChannelInstruction[bool]:
    step_bounds = get_step_starts(step_durations)
    instructions = []
    for cell_value, start, stop in lane.get_value_spans():
        length = number_ticks(step_bounds[start], step_bounds[stop], time_step * ns)
        if isinstance(cell_value, bool):
            instructions.append(ChannelPattern([cell_value]) * length)
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
                ChannelPattern([True]) * num_ticks_high
                + ChannelPattern([False]) * num_ticks_low
            )
            a, b = clock_pattern.split(split_position)
            clock_pattern = b + a
            pattern = (
                clock_pattern * num_clock_pulses + ChannelPattern([False]) * remainder
            )
            if not len(pattern) == length:
                raise RuntimeError(
                    f"Pattern length {len(pattern)} does not match expected length {length}"
                )
            print(f"{pattern=}")
            instructions.append(pattern)
        else:
            raise NotImplementedError(f"Unexpected value {cell_value} in digital lane")
    return ChannelInstruction.join(instructions, dtype=bool)


def compile_analog_lane(
    step_durations: Sequence[float],
    lane: AnalogLane,
    variables: VariableNamespace,
    time_step: int,
) -> ChannelInstruction[float]:
    return CompileAnalogLane(step_durations, lane, variables, time_step).compile()


@dataclass(slots=True)
class CompileAnalogLane:
    step_durations: Sequence[float]
    lane: AnalogLane
    variables: VariableNamespace
    time_step: int

    def compile(self) -> ChannelInstruction[float]:
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
                left, instruction = instruction.split(step_stop_tick - step_start_tick)
                instructions.append(left)
        return ChannelInstruction.join(instructions, dtype=float)

    def _compile_expression_cell(
        self, expression: Expression, start: float, stop: float
    ) -> ChannelInstruction[float]:
        variables = self.variables | units
        length = number_ticks(start, stop, self.time_step * ns)
        if _is_constant(expression):
            value = self._evaluate_expression(expression, variables)
            result = ChannelPattern([float(value)]) * length
        else:
            variables = variables | {
                DottedVariableName("t"): (
                    _compute_time_array(start, stop, self.time_step) - start
                )
                * ureg.s
            }
            result = ChannelPattern(self._evaluate_expression(expression, variables))
        if not len(result) == length:
            raise ShotEvaluationError(
                f"Expression '{expression}' evaluates to an array of length"
                f" {len(result)} while the expected length is {length}"
            )
        return result

    def _compile_ramp_cell(self, start_index: int) -> ChannelInstruction[float]:
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
        return ChannelPattern(result)

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
) -> ChannelInstruction[bool]:
    instructions = []
    for value, start, stop, _ in camera_instruction.triggers:
        length = number_ticks(start, stop, time_step * ns)
        instructions.append(ChannelPattern([value]) * length)
    return ChannelInstruction.join(instructions, dtype=bool)


def compile_clock_instruction(
    clock_requirements: Sequence[ClockInstruction], time_step: int
) -> ChannelInstruction[bool]:
    instructions = []

    for clock_instruction in clock_requirements:
        clock_start = start_tick(
            clock_instruction.start, clock_instruction.time_step * ns
        )
        clock_stop = stop_tick(clock_instruction.stop, clock_instruction.time_step * ns)
        multiplier, high, low = high_low_clicks(clock_instruction.time_step, time_step)
        clock_single_pulse = (
            ChannelPattern([True]) * high + ChannelPattern([False]) * low
        )
        clock_pulse_length = len(clock_single_pulse)

        clock_rep = clock_stop - clock_start
        if clock_instruction.order == ClockInstruction.StepInstruction.TriggerStart:
            if clock_rep == 0:
                pattern = ChannelPattern.empty(bool)
            else:
                pattern = clock_single_pulse + ChannelPattern([False]) * (
                    (clock_rep - 1) * clock_pulse_length
                )
        elif clock_instruction.order == ClockInstruction.StepInstruction.Clock:
            pattern = clock_single_pulse * clock_rep
        elif clock_instruction.order == ClockInstruction.StepInstruction.NoClock:
            pattern = ChannelPattern([False]) * clock_pulse_length * clock_rep
        else:
            raise NotImplementedError(
                f"Order {clock_instruction.order} not implemented"
            )
        instructions.append(pattern)
    length = number_ticks(0.0, clock_requirements[-1].stop, time_step * ns)
    return ChannelInstruction.join(instructions, dtype=bool).split(length)[0]



