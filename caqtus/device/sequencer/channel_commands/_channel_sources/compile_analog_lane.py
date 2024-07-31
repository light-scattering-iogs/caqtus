from __future__ import annotations

import collections
from collections.abc import Sequence, Mapping
from numbers import Real
from typing import assert_never, Optional, Any

import attrs
import numpy as np
import numpy.typing as npt
from pint.facets.plain import PlainQuantity

import caqtus.formatter as fmt
from caqtus.device.sequencer.instructions import (
    SequencerInstruction,
    Pattern,
    concatenate,
    ramp,
)
from caqtus.shot_compilation.compilation_contexts import ShotContext
from caqtus.shot_compilation.lane_compilers.timing import (
    start_tick,
    stop_tick,
    number_ticks,
    ns,
)
from caqtus.types.expression import Expression
from caqtus.types.recoverable_exceptions import InvalidValueError, InvalidTypeError
from caqtus.types.timelane import AnalogTimeLane, Ramp, Block
from caqtus.types.units import (
    ureg,
    Quantity,
    dimensionless,
    UnitLike,
    InvalidDimensionalityError,
    Unit,
)
from caqtus.types.variable_name import VariableName, DottedVariableName

TIME_VARIABLE = VariableName("t")


def compile_analog_lane(
    lane: AnalogTimeLane,
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

    step_time_boundaries = shot_context.get_step_bounds()

    # We do a first pass to compile the blocks that contain expressions and ignore
    # the ramps.
    # This is useful because the ramps need to know the value of the surrounding blocks
    # to be computed.
    # In addition, we can check that all expressions evaluates to the same unit.
    expression_results: dict[Block, ConstantBlockResult | TimeDependentBlockResult] = {}
    for block_index, block_value in enumerate(lane.block_values()):
        block_start_step, block_stop_step = lane.get_block_bounds(Block(block_index))
        block_start_time = step_time_boundaries[block_start_step]
        block_stop_time = step_time_boundaries[block_stop_step]
        if isinstance(block_value, Expression):
            expr_result = _compile_expression_block(
                block_value,
                shot_context.get_variables(),
                block_start_time,
                block_stop_time,
                time_step,
            )
            expression_results[Block(block_index)] = expr_result
        elif isinstance(block_value, Ramp):
            continue
        else:
            assert_never(block_value)

    if len(expression_results) == 0:
        raise InvalidValueError("Lane must contain at least one expression block")

    unique_units = get_unique_units(
        {block: result.unit for block, result in expression_results.items()}
    )
    assert len(unique_units) > 0

    if len(unique_units) > 1:
        error = InvalidDimensionalityError(
            "All expressions in the lane must evaluate to the same unit"
        )
        for unit, blocks in unique_units.items():
            error.add_note(
                f"Blocks {blocks} evaluate to {fmt.unit(unit or dimensionless)}"
            )
        raise error

    ramp_results: dict[Block, RampBlockResult] = {}
    for block_index, block_value in enumerate(lane.block_values()):
        if isinstance(block_value, Ramp):
            ramp_result = _compile_ramp_cell(
                lane,
                Block(block_index),
                expression_results,
                step_time_boundaries,
                time_step,
            )
            ramp_results[Block(block_index)] = ramp_result
        elif isinstance(block_value, Expression):
            continue
        else:
            assert_never(block_value)

    block_results = expression_results | ramp_results
    assert len(block_results) == lane.number_blocks
    assert len({result.unit for result in block_results.values()}) == 1

    instructions = (result.to_instruction() for result in block_results.values())

    return concatenate(*instructions)


def get_unique_units(
    units: Mapping[Block, Optional[UnitLike]]
) -> dict[Optional[UnitLike], list[Block]]:
    unique_units = collections.defaultdict(list)

    for block, unit in units.items():
        unique_units[unit].append(block)

    return unique_units


def _compile_expression_block(
    expression: Expression,
    variables: Mapping[DottedVariableName, Any],
    start_time: float,
    stop_time: float,
    time_step: int,
) -> ConstantBlockResult | TimeDependentBlockResult:
    length = number_ticks(start_time, stop_time, time_step * ns)
    if is_constant(expression):
        return evaluate_constant_expression(expression, variables, length)
    else:
        return evaluate_time_dependent_expression(
            expression, variables, start_time, stop_time, time_step
        )


def evaluate_constant_expression(
    expression: Expression,
    variables: Mapping[DottedVariableName, Any],
    length: int,
) -> ConstantBlockResult:
    value = expression.evaluate(variables)
    if isinstance(value, Quantity):
        in_base_units = value.to_base_units()
        magnitude = in_base_units.magnitude
        unit = in_base_units.units
        return ConstantBlockResult(
            value=float(magnitude),
            length=length,
            unit=unit if unit != dimensionless else None,
        )
    elif isinstance(value, Real):
        return ConstantBlockResult(
            value=float(value),
            length=length,
            unit=None,
        )
    else:
        raise InvalidValueError(
            f"{fmt.expression(expression)} does not evaluate to a number or a quantity"
            f" but to {fmt.type_(type(value))}",
        )


def evaluate_time_dependent_expression(
    expression: Expression,
    variables: Mapping[DottedVariableName, Any],
    start_time: float,
    stop_time: float,
    time_step: int,
) -> TimeDependentBlockResult:
    assert not is_constant(expression)

    time_values = get_time_array(start_time, stop_time, time_step) - start_time
    # The first time is not necessarily 0, it is the time of the first tick of the
    # block.
    # Same for the last time which is not necessarily stop_time - start_time, but the
    # time of the last tick of the block.
    # If a ramp precedes this block, we also want to know the value of the current block
    # at true t=0, so we compute this as well.
    # Same if a ramp follows this block, we want to know the value of the current block
    # at true t=stop_time - start_time.
    time_values = np.insert(
        time_values, [0, len(time_values)], [0, stop_time - start_time]
    )

    t = time_values * ureg.s
    variables = dict(variables) | {TIME_VARIABLE: t}
    evaluated = expression.evaluate(variables)

    if isinstance(evaluated, PlainQuantity):
        in_base_units = evaluated.to_base_units()
        magnitudes = in_base_units.magnitude
        if not isinstance(magnitudes, np.ndarray):
            raise InvalidTypeError(
                f"{fmt.expression(expression)} does not evaluate to a series of values"
            )
        unit = in_base_units.units
    elif isinstance(evaluated, np.ndarray):
        magnitudes = evaluated
        unit = None
    else:
        raise InvalidTypeError(
            f"{fmt.expression(expression)} does not evaluate to a series of values"
        )
    length = number_ticks(start_time, stop_time, time_step * ns)
    if magnitudes.shape != (length + 2,):
        raise InvalidValueError(
            f"{fmt.expression(expression)} evaluates to an array of shape"
            f" {magnitudes.shape} while a shape of {(length,)} is expected",
        )
    return TimeDependentBlockResult(
        values=magnitudes[1:-1].astype(np.float64),
        unit=unit if unit != dimensionless else None,
        initial_value=float(magnitudes[0]),
        final_value=float(magnitudes[-1]),
    )


def _compile_ramp_cell(
    lane: AnalogTimeLane,
    ramp_block: Block,
    expression_blocks: dict[Block, ConstantBlockResult | TimeDependentBlockResult],
    step_bounds: Sequence[float],
    time_step: int,
) -> RampBlockResult:
    previous_block = Block(ramp_block - 1)
    if previous_block < 0:
        raise InvalidValueError(f"There can't be a ramp at the beginning of a lane")
    next_block = Block(ramp_block + 1)
    if next_block >= lane.number_blocks:
        raise InvalidValueError(f"There can't be a ramp at the end of a lane")

    try:
        previous_block_result = expression_blocks[previous_block]
    except KeyError:
        raise InvalidValueError(
            f"Block {previous_block} that precedes a ramp must be an expression"
        )
    try:
        next_block_result = expression_blocks[next_block]
    except KeyError:
        raise InvalidValueError(
            f"Block {next_block} that follows a ramp must be an expression"
        )

    assert previous_block_result.unit == next_block_result.unit

    ramp_start_value = previous_block_result.get_final_value()
    ramp_end_value = next_block_result.get_initial_value()

    ramp_start_step, ramp_end_step = lane.get_block_bounds(ramp_block)

    ramp_start_time = step_bounds[ramp_start_step]
    ramp_end_time = step_bounds[ramp_end_step]

    return RampBlockResult.through_two_points(
        ramp_start_time,
        ramp_start_value,
        ramp_end_time,
        ramp_end_value,
        time_step,
        previous_block_result.unit,
    )


def is_constant(expression: Expression) -> bool:
    return TIME_VARIABLE not in expression.upstream_variables


def get_time_array(start: float, stop: float, time_step: int) -> np.ndarray:
    times = (
        np.arange(start_tick(start, time_step * ns), stop_tick(stop, time_step * ns))
        * time_step
        * ns
    )
    return times


@attrs.frozen
class ConstantBlockResult:
    """Result of compiling a constant block."""

    value: float
    length: int
    unit: Optional[Unit]

    def get_initial_value(self) -> float:
        return self.value

    def get_final_value(self) -> float:
        return self.value

    def to_instruction(self) -> SequencerInstruction[np.float64]:
        return Pattern([self.value]) * self.length


@attrs.frozen(eq=False)
class TimeDependentBlockResult:
    """Result of compiling a time-dependent block."""

    values: npt.NDArray[np.float64]
    unit: Optional[Unit]

    initial_value: float
    final_value: float

    def __eq__(self, other):
        if not isinstance(other, TimeDependentBlockResult):
            return NotImplemented
        return (
            np.allclose(self.values, other.values)
            and self.unit == other.unit
            and self.initial_value == other.initial_value
            and self.final_value == other.final_value
        )

    def get_initial_value(self) -> float:
        return self.initial_value

    def get_final_value(self) -> float:
        return self.final_value

    def to_instruction(self) -> SequencerInstruction[np.float64]:
        return Pattern(self.values, dtype=np.dtype(np.float64))


@attrs.frozen
class RampBlockResult:
    """Result of compiling a ramp block."""

    initial_value: float
    final_value: float
    length: int

    unit: Optional[Unit]

    @classmethod
    def through_two_points(
        cls,
        t0: float,
        v0: float,
        t1: float,
        v1: float,
        time_step: int,
        unit: Optional[UnitLike],
    ) -> RampBlockResult:
        def f(t: float) -> float:
            return (t - t0) / (t1 - t0) * (v1 - v0) + v0

        first_tick = start_tick(t0, time_step * ns)
        last_tick = stop_tick(t1, time_step * ns)

        first_tick_time = first_tick * time_step * ns
        last_tick_time = last_tick * time_step * ns

        initial_value = f(first_tick_time)
        final_value = f(last_tick_time)

        length = last_tick - first_tick

        return RampBlockResult(initial_value, final_value, length, unit)

    def to_instruction(self) -> SequencerInstruction[np.float64]:
        return ramp(self.initial_value, self.final_value, self.length)
