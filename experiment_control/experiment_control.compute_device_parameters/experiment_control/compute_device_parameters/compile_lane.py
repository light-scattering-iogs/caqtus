import math
from collections.abc import Sequence, Mapping, Iterable
from dataclasses import dataclass
from itertools import accumulate
from numbers import Real
from typing import SupportsFloat

import numpy as np

from expression import Expression
from parameter_types import is_analog_value, Parameter
from parameter_types.analog_value import magnitude_in_unit
from sequence.configuration import DigitalLane, AnalogLane, Ramp, Lane
from sequencer.channel import ChannelInstruction, ChannelPattern
from sequencer.channel.channel_instructions import ChannelType
from units import Quantity, ureg, units
from variable.name import DottedVariableName
from variable.namespace import VariableNamespace
from .camera_instruction import CameraInstruction
from .clock_instruction import ClockInstruction, ClockStepInstruction
from .evaluation_error import ShotEvaluationError


def empty_channel_instruction(
    default_value: ChannelType, step_durations: Sequence[float], time_step: float
) -> ChannelInstruction[ChannelType]:
    duration = sum(step_durations)
    length = int(duration / time_step)
    return ChannelPattern([default_value]) * length


def compile_lane(
    lane: Lane,
    step_durations: Sequence[float],
    time_step: float,
    variables: VariableNamespace,
) -> ChannelInstruction:
    if isinstance(lane, DigitalLane):
        return compile_digital_lane(step_durations, lane, time_step)
    elif isinstance(lane, AnalogLane):
        return compile_analog_lane(step_durations, lane, variables, time_step)
    else:
        raise NotImplementedError(f"Unknown lane type {type(lane)}")


def compile_digital_lane(
    step_durations: Sequence[float],
    lane: DigitalLane,
    time_step: float,
) -> ChannelInstruction[bool]:
    step_bounds = get_step_bounds(step_durations)
    instructions = []
    for cell_value, start, stop in lane.get_value_spans():
        length = number_ticks(step_bounds[start], step_bounds[stop], time_step)
        instructions.append(ChannelPattern([cell_value]) * length)
    return ChannelInstruction.join(instructions, dtype=bool)


def number_ticks(
    start_time: SupportsFloat, stop_time: SupportsFloat, time_step: SupportsFloat
) -> int:
    """Returns the number of ticks between start_time and stop_time."""

    return stop_tick(stop_time, time_step) - start_tick(start_time, time_step)


def start_tick(start_time: SupportsFloat, time_step: SupportsFloat) -> int:
    """Returns the included first tick index of the step starting at start_time."""

    return math.floor(float(start_time) / float(time_step))


def stop_tick(stop_time: SupportsFloat, time_step: SupportsFloat) -> int:
    """Returns the excluded last tick index of the step ending at stop_time."""

    return math.floor((float(stop_time)) / float(time_step))


def get_step_bounds(step_durations: Iterable[float]) -> Sequence[float]:
    return [0.0] + list((accumulate(step_durations)))


def compile_analog_lane(
    step_durations: Sequence[float],
    lane: AnalogLane,
    variables: VariableNamespace,
    time_step: float,
) -> ChannelInstruction[float]:
    return CompileAnalogLane(step_durations, lane, variables, time_step).compile()


@dataclass(slots=True)
class CompileAnalogLane:
    step_durations: Sequence[float]
    lane: AnalogLane
    variables: VariableNamespace
    time_step: float

    def compile(self) -> ChannelInstruction[float]:
        step_bounds = get_step_bounds(self.step_durations)
        instructions = []
        for cell, start, stop in self.lane.get_value_spans():
            length = number_ticks(step_bounds[start], step_bounds[stop], self.time_step)
            if isinstance(cell, Expression):
                instructions.append(self._compile_expression_cell(cell, length))
            elif isinstance(cell, Ramp):
                instructions.append(self._compile_ramp_cell(start - 1, stop, length))
        return ChannelInstruction.join(instructions, dtype=float)

    def _compile_expression_cell(
        self, expression: Expression, length: int
    ) -> ChannelInstruction[float]:
        variables = self.variables | units
        if _is_constant(expression):
            result = (
                ChannelPattern(
                    [float(self._evaluate_expression(expression, variables))]
                )
                * length
            )
        else:
            variables = variables | {
                DottedVariableName("t"): _compute_time_array(length, self.time_step)
            }
            result = ChannelPattern(self._evaluate_expression(expression, variables))
        if not len(result) == length:
            raise ShotEvaluationError(
                f"Expression '{expression}' evaluates to an array of length"
                f" {len(result)} while the expected length is {length}"
            )
        return result

    def _compile_ramp_cell(
        self, previous_index: int, next_index: int, length: int
    ) -> ChannelInstruction[float]:
        previous_step_duration = sum(
            self.step_durations[
                self.lane.start_index(previous_index) : self.lane.end_index(
                    previous_index
                )
            ]
        )
        variables = (
            self.variables
            | units
            | {DottedVariableName("t"): previous_step_duration * ureg.s}
        )
        previous_value = self._evaluate_expression(
            self.lane.get_effective_value(previous_index), variables
        )

        variables = self.variables | units | {DottedVariableName("t"): 0.0 * ureg.s}
        next_value = self._evaluate_expression(
            self.lane.get_effective_value(next_index), variables
        )
        return ChannelPattern(
            np.linspace(previous_value, next_value, length), dtype=float
        )

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


def _compute_time_array(length: int, time_step: float) -> Quantity:
    return (np.arange(length) * time_step) * ureg.s


def compile_camera_instruction(
    camera_instruction: CameraInstruction,
    time_step: float,
) -> ChannelInstruction[bool]:
    instructions = []
    for value, start, stop in camera_instruction.triggers:
        length = number_ticks(start, stop, time_step)
        instructions.append(ChannelPattern([value]) * length)
    return ChannelInstruction.join(instructions, dtype=bool)


def compile_clock_instruction(
    clock_requirements: Sequence[ClockInstruction], time_step: float
) -> ChannelInstruction[bool]:
    instructions = []

    # must ensure here that the clock line only goes up at a multiple of the clock time step.
    # The clock time step must be a multiple of the channel time step.
    # Since the clock must go up and down in a single clock step, it must be at least twice the channel time step.
    for clock_instruction in clock_requirements:
        multiplier, high, low = high_low_clicks(clock_instruction.time_step, time_step)
        start = start_tick(clock_instruction.start, time_step)
        stop = stop_tick(clock_instruction.stop, time_step)
        length = number_ticks(start, stop, time_step)

        # All 3 values below are given in time_step units:
        clock_start = (
            start_tick(clock_instruction.start, clock_instruction.time_step)
            * multiplier
        )
        clock_stop = (
            stop_tick(clock_instruction.stop, clock_instruction.time_step) * multiplier
        )
        clock_length = (
            number_ticks(clock_start, clock_stop, clock_instruction.time_step)
            * multiplier
        )

        before = ChannelPattern([False]) * (clock_start - start)
        after = ChannelPattern([False]) * (stop - clock_stop)
        if clock_instruction.order == ClockStepInstruction.TriggerStart:
            middle = ChannelPattern([True]) * high + ChannelPattern([False]) * (
                clock_length - high
            )
        elif clock_instruction.order == ClockStepInstruction.Clock:
            middle = (ChannelPattern([True]) * high + ChannelPattern([False]) * low) * (
                clock_length // multiplier
            )
        else:
            raise NotImplementedError(
                f"Order {clock_instruction.order} not implemented"
            )
        instructions.append(before + middle + after)
    return ChannelInstruction.join(instructions, dtype=bool)


def high_low_clicks(
    clock_time_step: float, sequencer_time_step: float
) -> tuple[int, int, int]:
    """Return the number of steps the sequencer must be high then low to produce a clock pulse."""
    if not clock_time_step >= 2 * sequencer_time_step:
        raise ValueError(
            "Clock time step must be at least twice the sequencer time step"
        )
    div, mod = divmod(clock_time_step, sequencer_time_step)
    if not mod == 0:
        raise ValueError(
            "Clock time step must be an integer multiple of the sequencer time step"
        )
    if div % 2 == 0:
        return div, div // 2, div // 2
    else:
        return div, div // 2 + 1, div // 2
