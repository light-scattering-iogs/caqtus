from collections.abc import Sequence, Mapping
from typing import assert_never, Optional, Any

import numpy as np

import caqtus.formatter as fmt
from caqtus.device.sequencer.instructions import (
    SequencerInstruction,
    Pattern,
    concatenate,
)
from caqtus.shot_compilation.compilation_contexts import ShotContext
from caqtus.shot_compilation.lane_compilers.timing import (
    start_tick,
    stop_tick,
    number_ticks,
    ns,
)
from caqtus.types.expression import Expression
from caqtus.types.parameter import (
    AnalogValue,
    is_analog_value,
    is_quantity,
    magnitude_in_unit,
)
from caqtus.types.recoverable_exceptions import InvalidValueError
from caqtus.types.timelane import AnalogTimeLane, Ramp
from caqtus.types.units import ureg
from caqtus.types.variable_name import VariableName, DottedVariableName

TIME_VARIABLE = VariableName("t")


def compile_analog_lane(
    lane: AnalogTimeLane,
    unit: Optional[str],
    time_step: int,
    shot_context: ShotContext,
) -> SequencerInstruction[np.float64]:
    """Compile the lane to a sequencer instruction.

    This function discretizes the lane time and replaces the expressions in the
    lane with the given variable values.
    It also evaluates the ramps in the lane.
    The sequencer instruction returned is the magnitude of the lane in the given
    unit.
    """
    step_names = shot_context.get_step_names()
    step_durations = shot_context.get_step_durations()
    if len(lane) != len(step_names):
        raise ValueError(
            f"Number of steps in lane ({len(lane)}) does not match number of"
            f" step names ({len(step_names)})"
        )
    if len(lane) != len(step_durations):
        raise ValueError(
            f"Number of steps in lane ({len(lane)}) does not match number of"
            f" step durations ({len(step_durations)})"
        )

    step_bounds = shot_context.get_step_bounds()
    instructions = []
    for cell_value, (cell_start_index, cell_stop_index) in zip(
        lane.values(), lane.bounds()
    ):
        cell_start_time = step_bounds[cell_start_index]
        cell_stop_time = step_bounds[cell_stop_index]
        if isinstance(cell_value, Expression):
            instruction = _compile_expression_cell(
                shot_context.get_variables(),
                cell_value,
                cell_start_time,
                cell_stop_time,
                time_step,
                unit,
            )
        elif isinstance(cell_value, Ramp):
            instruction = _compile_ramp_cell(
                lane,
                cell_start_index,
                cell_stop_index,
                step_bounds,
                shot_context.get_variables(),
                time_step,
                unit,
            )
        else:
            assert_never(cell_value)
        instructions.append(instruction)
    return concatenate(*instructions)


def _compile_expression_cell(
    variables: Mapping[DottedVariableName, Any],
    expression: Expression,
    start: float,
    stop: float,
    time_step: int,
    unit: Optional[str],
) -> SequencerInstruction[np.float64]:
    length = number_ticks(start, stop, time_step * ns)
    if is_constant(expression):
        evaluated = _evaluate_expression(expression, variables)
        value = magnitude_in_unit(evaluated, unit)
        result = Pattern([float(value)], dtype=np.float64) * length
    else:
        variables = dict(variables) | {
            TIME_VARIABLE: (get_time_array(start, stop, time_step) - start) * ureg.s
        }
        evaluated = _evaluate_expression(expression, variables)
        result = Pattern(magnitude_in_unit(evaluated, unit), dtype=np.float64)
    if not len(result) == length:
        raise ValueError(
            f"{expression} evaluates to an array of length {len(result)}"
            f" while {length} is expected",
        )
    return result


def _compile_ramp_cell(
    lane: AnalogTimeLane,
    start_index: int,
    stop_index: int,
    step_bounds: Sequence[float],
    variables: Mapping[DottedVariableName, Any],
    time_step: int,
    unit: Optional[str],
) -> SequencerInstruction[np.float64]:
    t0 = step_bounds[start_index]
    t1 = step_bounds[stop_index]
    previous_step_duration = (
        step_bounds[lane.get_bounds(start_index - 1)[1]]
        - step_bounds[lane.get_bounds(start_index - 1)[0]]
    )
    v = dict(variables) | {TIME_VARIABLE: previous_step_duration * ureg.s}
    ramp_start = _evaluate_expression(lane[start_index - 1], v)
    if is_quantity(ramp_start):
        ramp_start = ramp_start.to_base_units()

    v = dict(variables) | {TIME_VARIABLE: 0.0 * ureg.s}
    ramp_end = _evaluate_expression(lane[stop_index], v)
    if is_quantity(ramp_end):
        ramp_end = ramp_end.to_base_units()

    # Don't need to give units to t, because we'll be dividing by t1 - t0 anyway
    t = get_time_array(t0, t1, time_step)
    result = (t - t0) / (t1 - t0) * (ramp_end - ramp_start) + ramp_start

    return Pattern(magnitude_in_unit(result, unit), dtype=np.float64)


def _evaluate_expression(
    expression: Expression, variables: Mapping[DottedVariableName, Any]
) -> AnalogValue:
    value = expression.evaluate(variables)
    if not is_analog_value(value):
        raise InvalidValueError(
            f"{fmt.expression(expression)} evaluates to a non-analog value"
        )
    return value


def is_constant(expression: Expression) -> bool:
    return TIME_VARIABLE not in expression.upstream_variables


def get_time_array(start: float, stop: float, time_step: int) -> np.ndarray:
    times = (
        np.arange(start_tick(start, time_step * ns), stop_tick(stop, time_step * ns))
        * time_step
        * ns
    )
    return times
