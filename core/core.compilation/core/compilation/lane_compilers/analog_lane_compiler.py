from collections.abc import Sequence
from typing import assert_never, Optional

import numpy as np

from core.device.sequencer.instructions import SequencerInstruction, Pattern, join
from core.session.shot.timelane import AnalogTimeLane, Ramp
from core.types.expression import Expression
from core.types.parameter import (
    AnalogValue,
    is_analog_value,
    is_quantity,
    magnitude_in_unit,
)
from core.types.units import ureg
from core.types.variable_name import DottedVariableName
from .evaluate_step_durations import evaluate_step_durations
from .timing import get_step_bounds, start_tick, stop_tick, number_ticks, ns
from ..unit_namespace import units
from ..variable_namespace import VariableNamespace


class AnalogLaneCompiler:
    def __init__(
        self,
        lane: AnalogTimeLane,
        step_names: Sequence[str],
        step_durations: Sequence[Expression],
        unit: Optional[str],
    ):
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
        self.lane = lane
        self.steps = list(zip(step_names, step_durations))
        self.unit = unit

    def compile(
        self, variables: VariableNamespace, time_step: int
    ) -> SequencerInstruction[np.float64]:
        step_durations = evaluate_step_durations(self.steps, variables)
        step_bounds = get_step_bounds(step_durations)
        instructions = []
        for cell_value, (cell_start_index, cell_stop_index) in zip(
            self.lane.values(), self.lane.bounds()
        ):
            cell_start_time = step_bounds[cell_start_index]
            cell_stop_time = step_bounds[cell_stop_index]
            if isinstance(cell_value, Expression):
                instruction = self._compile_expression_cell(
                    variables | units,
                    cell_value,
                    cell_start_time,
                    cell_stop_time,
                    time_step,
                )
            elif isinstance(cell_value, Ramp):
                instruction = self._compile_ramp_cell(
                    cell_start_index, cell_stop_index, step_bounds, variables, time_step
                )
            else:
                assert_never(cell_value)
            instructions.append(instruction)
        return join(*instructions)

    def _compile_expression_cell(
        self,
        variables,
        expression: Expression,
        start: float,
        stop: float,
        time_step: int,
    ) -> SequencerInstruction[np.float64]:
        length = number_ticks(start, stop, time_step * ns)
        if is_constant(expression):
            evaluated = self._evaluate_expression(expression, variables)
            value = magnitude_in_unit(evaluated, self.unit)
            result = Pattern([float(value)], dtype=np.float64) * length
        else:
            variables = variables | {
                DottedVariableName("t"): (
                    get_time_array(start, stop, time_step) - start
                )
                * ureg.s
            }
            evaluated = self._evaluate_expression(expression, variables)
            result = Pattern(magnitude_in_unit(evaluated, self.unit), dtype=np.float64)
        if not len(result) == length:
            raise ValueError(
                f"Expression <{expression}> evaluates to an array of length"
                f" {len(result)} while the expected length is {length}"
            )
        return result

    def _compile_ramp_cell(
        self,
        start_index: int,
        stop_index: int,
        step_bounds: Sequence[float],
        variables,
        time_step: int,
    ) -> SequencerInstruction[np.float64]:
        t0 = step_bounds[start_index]
        t1 = step_bounds[stop_index]
        previous_step_duration = (
            step_bounds[self.lane.get_bounds(start_index - 1)[1]]
            - step_bounds[self.lane.get_bounds(start_index - 1)[0]]
        )
        v = (
            variables
            | units
            | {DottedVariableName("t"): previous_step_duration * ureg.s}
        )
        previous_value = self._evaluate_expression(self.lane[start_index - 1], v)
        if is_quantity(previous_value):
            previous_value = previous_value.to_base_units()

        v = variables | units | {DottedVariableName("t"): 0.0 * ureg.s}
        next_value = self._evaluate_expression(self.lane[stop_index], v)
        if is_quantity(next_value):
            next_value = next_value.to_base_units()

        t = get_time_array(t0, t1, time_step)
        result = (t - t0) / (t1 - t0) * (next_value - previous_value) + previous_value

        return Pattern(magnitude_in_unit(result, self.unit), dtype=np.float64)

    @staticmethod
    def _evaluate_expression(expression: Expression, variables) -> AnalogValue:
        try:
            value = expression.evaluate(variables | units)
        except Exception as e:
            raise ValueError(f"Could not evaluate expression <{expression}>") from e
        if not is_analog_value(value):
            raise ValueError(
                f"Expression <{expression}> evaluates to a non-analog value ({value})"
            )
        return value


def is_constant(expression: Expression) -> bool:
    return "t" not in expression.upstream_variables


def get_time_array(start: float, stop: float, time_step: int) -> np.ndarray:
    times = (
        np.arange(start_tick(start, time_step * ns), stop_tick(stop, time_step * ns))
        * time_step
        * ns
    )
    return times
