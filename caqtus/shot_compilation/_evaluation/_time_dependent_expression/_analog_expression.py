import functools
from typing import assert_type, assert_never

import attrs
import numpy as np

import caqtus_parsing.nodes as nodes
from caqtus.shot_compilation.timed_instructions import (
    TimedInstruction,
    Pattern,
    create_ramp,
    Concatenated,
    Repeated,
    Ramp,
)
from caqtus.shot_compilation.timing import Time, number_ticks, start_tick, stop_tick
from caqtus.types.parameter import Parameters
from caqtus.types.units import BaseUnit, dimensionless, Quantity
from ._is_time_dependent import is_time_dependent
from .._evaluate_scalar_expression import evaluate_expression


@attrs.define
class AnalogInstruction:
    magnitudes: TimedInstruction[np.float64]
    units: BaseUnit


def evaluate_analog_ast(
    ast: nodes.Expression, parameters: Parameters, t1: Time, t2: Time, timestep: Time
) -> AnalogInstruction:
    if not is_time_dependent(ast):
        value = evaluate_expression(ast, parameters)
        length = number_ticks(t1, t2, timestep)
        if isinstance(value, (bool, int, float)):
            return AnalogInstruction(
                magnitudes=Pattern([float(value)]) * length,
                units=dimensionless,
            )
        else:
            assert_type(value, Quantity[float])
            in_base_units = value.to_base_units()
            return AnalogInstruction(
                magnitudes=Pattern([in_base_units.magnitude]) * length,
                units=in_base_units.units,
            )
    else:
        match ast:
            case int() | float() | nodes.Quantity():
                raise AssertionError("Unreachable")
            case nodes.Variable(name=name):
                if name != "t":
                    raise AssertionError("Unreachable")
                tick_start = start_tick(t1, timestep)
                tick_stop = stop_tick(t2, timestep)
                value_start = tick_start * timestep - t1
                value_stop = tick_stop * timestep - t1
                length = tick_stop - tick_start
                return AnalogInstruction(
                    magnitudes=create_ramp(value_start, value_stop, length),
                    units=dimensionless,
                )
            case nodes.Call():
                raise NotImplementedError("Function calls are not supported.")
            case nodes.Plus() | nodes.Minus() as unary_operator:
                return evaluate_unary_operator(
                    unary_operator, parameters, t1, t2, timestep
                )
            case _:
                assert_never(ast)


def evaluate_unary_operator(
    unary_operator: nodes.UnaryOperator,
    parameters: Parameters,
    t1: Time,
    t2: Time,
    timestep: Time,
) -> AnalogInstruction:
    operand = evaluate_analog_ast(unary_operator.operand, parameters, t1, t2, timestep)
    match unary_operator:
        case nodes.Plus():
            return operand
        case nodes.Minus():
            return AnalogInstruction(
                magnitudes=negate(operand.magnitudes),
                units=operand.units,
            )
        case _:
            assert_never(unary_operator)


@functools.singledispatch
def negate(instruction) -> TimedInstruction[np.float64]:
    raise NotImplementedError(f"Negation of {type(instruction)} is not supported.")


@negate.register(Pattern)
def negate_pattern(pattern: Pattern[np.float64]) -> Pattern[np.float64]:
    return Pattern.create_without_copy(-pattern.array)


@negate.register(Concatenated)
def negate_concatenated(
    concatenated: Concatenated[np.float64],
) -> Concatenated[np.float64]:
    return Concatenated(*(negate(instr) for instr in concatenated.instructions))


@negate.register(Repeated)
def negate_repeated(repeated: Repeated[np.float64]) -> Repeated[np.float64]:
    return Repeated(repeated.repetitions, negate(repeated.instruction))


@negate.register(Ramp)
def negate_ramp(ramp: Ramp[np.float64]) -> TimedInstruction[np.float64]:
    return create_ramp(-ramp.start, -ramp.stop, len(ramp))
