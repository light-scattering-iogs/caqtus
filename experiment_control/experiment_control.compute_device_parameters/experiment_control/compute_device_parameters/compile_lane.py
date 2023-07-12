import logging
import math
from collections.abc import Sequence, Mapping, Iterable
from dataclasses import dataclass
from itertools import accumulate
from numbers import Real

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
from .clock_instruction import ClockInstruction
from .evaluation_error import ShotEvaluationError

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ns = 1e-9


def empty_channel_instruction(
    default_value: ChannelType, step_durations: Sequence[float], time_step: int
) -> ChannelInstruction[ChannelType]:
    duration = sum(step_durations)
    length = number_ticks(0.0, duration, time_step)
    return ChannelPattern([default_value]) * length


def compile_lane(
    lane: Lane,
    step_durations: Sequence[float],
    time_step: int,
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
    time_step: int,
) -> ChannelInstruction[bool]:
    step_bounds = get_step_bounds(step_durations)
    instructions = []
    for cell_value, start, stop in lane.get_value_spans():
        length = number_ticks(step_bounds[start], step_bounds[stop], time_step)
        instructions.append(ChannelPattern([cell_value]) * length)
    return ChannelInstruction.join(instructions, dtype=bool)


def number_ticks(start_time: float, stop_time: float, time_step: int) -> int:
    """Returns the number of ticks between start_time and stop_time.

    Args:
        start_time: The start time in seconds.
        stop_time: The stop time in seconds.
        time_step: The time step in nanoseconds.
    """

    return stop_tick(stop_time, time_step) - start_tick(start_time, time_step)


def start_tick(start_time: float, time_step: int) -> int:
    """Returns the included first tick index of the step starting at start_time."""

    return math.ceil(start_time / ns / time_step)


def stop_tick(stop_time: float, time_step: int) -> int:
    """Returns the excluded last tick index of the step ending at stop_time."""

    return math.ceil(stop_time / ns / time_step)


def get_step_bounds(step_durations: Iterable[float]) -> list[float]:
    """Returns the step bounds for the given step durations.

    For an iterable of step durations [d_0, d_1, ..., d_n], the step bounds are
    [0, d_0, d_0 + d_1, ..., d_0 + ... + d_n].
    """

    return [0.0] + list((accumulate(step_durations)))


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
        step_bounds = get_step_bounds(self.step_durations)
        instructions = []
        for cell, start, stop in self.lane.get_value_spans():
            if isinstance(cell, Expression):
                instructions.append(
                    self._compile_expression_cell(
                        cell, step_bounds[start], step_bounds[stop]
                    )
                )
            elif isinstance(cell, Ramp):
                instructions.append(self._compile_ramp_cell(start))
        return ChannelInstruction.join(instructions, dtype=float)

    def _compile_expression_cell(
        self, expression: Expression, start: float, stop: float
    ) -> ChannelInstruction[float]:
        variables = self.variables | units
        length = number_ticks(start, stop, self.time_step)
        if _is_constant(expression):
            result = (
                ChannelPattern(
                    [float(self._evaluate_expression(expression, variables))]
                )
                * length
            )
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
        step_bounds = get_step_bounds(self.step_durations)
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
        t = _compute_time_array(t0, t1, self.time_step)
        return ChannelPattern(
            (t - t0) / (t1 - t0) * (next_value - previous_value) + previous_value
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


def _compute_time_array(start: float, stop: float, time_step: int) -> np.ndarray:
    times = (
        np.arange(start_tick(start, time_step), stop_tick(stop, time_step))
        * time_step
        * ns
    )
    return times


def compile_camera_instruction(
    camera_instruction: CameraInstruction,
    time_step: int,
) -> ChannelInstruction[bool]:
    instructions = []
    for value, start, stop in camera_instruction.triggers:
        length = number_ticks(start, stop, time_step)
        instructions.append(ChannelPattern([value]) * length)
    return ChannelInstruction.join(instructions, dtype=bool)


def compile_clock_instruction(
    clock_requirements: Sequence[ClockInstruction], time_step: int
) -> ChannelInstruction[bool]:
    instructions = []

    # must ensure here that the clock line only goes up at a multiple of the clock time step.
    # The clock time step must be a multiple of the channel time step.
    # Since the clock must go up and down in a single clock step, it must be at least twice the channel time step.
    for clock_instruction in clock_requirements:
        multiplier, high, low = high_low_clicks(clock_instruction.time_step, time_step)
        start = start_tick(clock_instruction.start, time_step)
        stop = stop_tick(clock_instruction.stop, time_step)

        # All 3 values below are given in time_step units:
        clock_start = (
            start_tick(clock_instruction.start, clock_instruction.time_step)
            * multiplier
        )
        clock_stop = (
            stop_tick(clock_instruction.stop, clock_instruction.time_step) * multiplier
        )
        clock_length = (
            number_ticks(
                clock_instruction.start,
                clock_instruction.stop,
                clock_instruction.time_step,
            )
            * multiplier
        )

        try:
            before = ChannelPattern([False]) * (clock_start - start)
        except ValueError:
            logger.debug(f"{clock_instruction.start=}")
            logger.debug(f"{clock_start=} {start=}")
            logger.debug(f"{time_step=}")
            raise
        after = ChannelPattern([False]) * (stop - clock_stop)
        if clock_instruction.order == ClockInstruction.StepInstruction.TriggerStart:
            middle = ChannelPattern([True]) * high + ChannelPattern([False]) * (
                clock_length - high
            )
        elif clock_instruction.order == ClockInstruction.StepInstruction.Clock:
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
    clock_time_step: int, sequencer_time_step: int
) -> tuple[int, int, int]:
    """Return the number of steps the sequencer must be high then low to produce a clock pulse."""
    if not clock_time_step >= 2 * sequencer_time_step:
        raise ValueError(
            "Clock time step must be at least twice the sequencer time step"
        )
    div, mod = divmod(clock_time_step, sequencer_time_step)
    if not mod == 0:
        logger.debug(f"{clock_time_step=}, {sequencer_time_step=}, {div=}, {mod=}")
        raise ValueError(
            "Clock time step must be an integer multiple of the sequencer time step"
        )
    if div % 2 == 0:
        return div, div // 2, div // 2
    else:
        return div, div // 2 + 1, div // 2
