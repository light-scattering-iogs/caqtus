import functools
from typing import assert_never, assert_type

import attrs
import numpy as np
from caqtus_parsing import (
    AST,
    BinaryOperation,
    BinaryOperator,
    Call,
    Float,
    Identifier,
    Integer,
    UnaryOperation,
    UnaryOperator,
)
from caqtus_parsing import (
    Quantity as QuantityNode,
)

from caqtus.shot_compilation.timed_instructions import (
    Concatenated,
    Pattern,
    Ramp,
    Repeated,
    TimedInstruction,
    concatenate,
    create_ramp,
    merge_instructions,
)
from caqtus.shot_compilation.timing import Time, number_ticks, start_tick, stop_tick
from caqtus.types.parameter import Parameters
from caqtus.types.units import (
    SECOND,
    BaseUnit,
    InvalidDimensionalityError,
    Quantity,
    Unit,
    dimensionless,
)

from .._evaluate_scalar_expression import evaluate_expression
from ._is_time_dependent import is_time_dependent


@attrs.define
class AnalogInstruction:
    magnitudes: TimedInstruction[np.float64]
    units: BaseUnit


def evaluate_analog_ast(
    ast: AST, parameters: Parameters, t1: Time, t2: Time, timestep: Time
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
            case Integer() | Float() | QuantityNode():
                raise AssertionError("Unreachable")
            case Identifier(name):
                if name != "t":
                    raise AssertionError("Unreachable")
                tick_start = start_tick(t1, timestep)
                tick_stop = stop_tick(t2, timestep)
                value_start = tick_start * timestep - t1
                value_stop = tick_stop * timestep - t1
                length = tick_stop - tick_start
                return AnalogInstruction(
                    magnitudes=create_ramp(value_start, value_stop, length),
                    units=SECOND,
                )
            case Call():
                raise NotImplementedError(
                    "Time dependent function calls are not yet supported."
                )
            case UnaryOperation(operator, operand):
                return evaluate_unary_operator(
                    operator, operand, parameters, t1, t2, timestep
                )
            case BinaryOperation(operator, lhs, rhs):
                left = evaluate_analog_ast(lhs, parameters, t1, t2, timestep)
                right = evaluate_analog_ast(rhs, parameters, t1, t2, timestep)
                match operator:
                    case BinaryOperator.Times:
                        units = left.units * right.units
                        assert isinstance(units, Unit)
                        return AnalogInstruction(
                            magnitudes=multiply(left.magnitudes, right.magnitudes),
                            units=units.to_base(),
                        )
                    case BinaryOperator.Div:
                        units = left.units / right.units
                        assert isinstance(units, Unit)
                        return AnalogInstruction(
                            magnitudes=divide(left.magnitudes, right.magnitudes),
                            units=units.to_base(),
                        )
                    case BinaryOperator.Plus:
                        if left.units != right.units:
                            raise InvalidDimensionalityError(
                                f"Cannot add {lhs} with units {left.units} to "
                                f"{rhs} with units {right.units}."
                            )
                        return AnalogInstruction(
                            magnitudes=add(left.magnitudes, right.magnitudes),
                            units=left.units,
                        )
                    case BinaryOperator.Minus:
                        if left.units != right.units:
                            raise InvalidDimensionalityError(
                                f"Cannot subtract {lhs} with units {left.units} from "
                                f"{rhs} with units {right.units}."
                            )
                        return AnalogInstruction(
                            magnitudes=add(left.magnitudes, negate(right.magnitudes)),
                            units=left.units,
                        )
                    case BinaryOperator.Times.Pow:
                        raise NotImplementedError(
                            "Power operator is not yet supported for time dependent "
                            "expressions."
                        )
                    case _:
                        assert_never(operator)
            case _:
                assert_never(ast)


def evaluate_unary_operator(
    unary_operator: UnaryOperator,
    operand: AST,
    parameters: Parameters,
    t1: Time,
    t2: Time,
    timestep: Time,
) -> AnalogInstruction:
    evaluated = evaluate_analog_ast(operand, parameters, t1, t2, timestep)
    match unary_operator:
        case UnaryOperator.Neg:
            return AnalogInstruction(
                magnitudes=negate(evaluated.magnitudes),
                units=evaluated.units,
            )
        case UnaryOperator.Plus:
            return AnalogInstruction(
                magnitudes=evaluated.magnitudes,
                units=evaluated.units,
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


def multiply(
    a: TimedInstruction[np.float64], b: TimedInstruction[np.float64]
) -> TimedInstruction[np.float64]:
    merged = merge_instructions(left=a, right=b)
    return _multiply(merged)


@functools.singledispatch
def _multiply(instruction) -> TimedInstruction[np.float64]:
    raise NotImplementedError(
        f"Multiplication of {type(instruction)} is not supported."
    )


@_multiply.register(Pattern)
def _multiply_pattern(pattern: Pattern[np.void]) -> Pattern[np.float64]:
    left_array = pattern["left"].array
    right_array = pattern["right"].array
    return Pattern.create_without_copy(left_array * right_array)


@_multiply.register(Concatenated)
def _multiply_concatenated(
    concatenated: Concatenated[np.void],
) -> TimedInstruction[np.float64]:
    return concatenate(*(_multiply(instr) for instr in concatenated.instructions))


@_multiply.register(Repeated)
def _multiply_repeated(repeated: Repeated[np.void]) -> TimedInstruction[np.float64]:
    return repeated.repetitions * _multiply(repeated.instruction)


@_multiply.register(Ramp)
def _multiply_ramp(ramp: Ramp[np.void]) -> TimedInstruction[np.float64]:
    left = ramp["left"]
    right = ramp["right"]

    a2 = left.slope * right.slope
    if a2 == 0:
        a1 = left.slope * right.intercept + right.slope * left.intercept
        a0 = left.intercept * right.intercept
        stop = a0 + a1 * len(ramp)
        return create_ramp(a0, stop, len(ramp))
    else:
        return _multiply(ramp.to_pattern())


def divide(
    a: TimedInstruction[np.float64], b: TimedInstruction[np.float64]
) -> TimedInstruction[np.float64]:
    merged = merge_instructions(left=a, right=b)
    return _divide(merged)


@functools.singledispatch
def _divide(instruction) -> TimedInstruction[np.float64]:
    raise NotImplementedError(f"Division of {type(instruction)} is not supported.")


@_divide.register(Pattern)
def _divide_pattern(pattern: Pattern[np.void]) -> Pattern[np.float64]:
    left_array = pattern["left"].array
    right_array = pattern["right"].array
    if np.any(right_array == 0):
        raise ZeroDivisionError("Division by zero in pattern division.")
    result = left_array / right_array
    return Pattern.create_without_copy(result)


@_divide.register(Concatenated)
def _divide_concatenated(
    concatenated: Concatenated[np.void],
) -> TimedInstruction[np.float64]:
    return concatenate(*(_divide(instr) for instr in concatenated.instructions))


@_divide.register(Repeated)
def _divide_repeated(repeated: Repeated[np.void]) -> TimedInstruction[np.float64]:
    return repeated.repetitions * _divide(repeated.instruction)


@_divide.register(Ramp)
def _divide_ramp(ramp: Ramp[np.void]) -> TimedInstruction[np.float64]:
    left = ramp["left"]
    right = ramp["right"]

    if right.slope == 0:
        if right.intercept == 0:
            raise ZeroDivisionError("Division by zero in ramp division.")
        a1 = left.slope / right.intercept
        a0 = left.intercept / right.intercept
        stop = a0 + a1 * len(ramp)
        return create_ramp(a0, stop, len(ramp))
    else:
        return _divide(ramp.to_pattern())


def add(
    a: TimedInstruction[np.float64], b: TimedInstruction[np.float64]
) -> TimedInstruction[np.float64]:
    merged = merge_instructions(left=a, right=b)
    return _add(merged)


@functools.singledispatch
def _add(instruction) -> TimedInstruction[np.float64]:
    raise NotImplementedError(f"Addition of {type(instruction)} is not supported.")


@_add.register(Pattern)
def _add_pattern(pattern: Pattern[np.void]) -> Pattern[np.float64]:
    left_array = pattern["left"].array
    right_array = pattern["right"].array
    return Pattern.create_without_copy(left_array + right_array)


@_add.register(Concatenated)
def _add_concatenated(
    concatenated: Concatenated[np.void],
) -> TimedInstruction[np.float64]:
    return concatenate(*(_add(instr) for instr in concatenated.instructions))


@_add.register(Repeated)
def _add_repeated(repeated: Repeated[np.void]) -> TimedInstruction[np.float64]:
    return repeated.repetitions * _add(repeated.instruction)


@_add.register(Ramp)
def _add_ramp(ramp: Ramp[np.void]) -> TimedInstruction[np.float64]:
    left = ramp["left"]
    right = ramp["right"]

    a1 = left.slope + right.slope
    a0 = left.intercept + right.intercept
    stop = a0 + a1 * len(ramp)
    return create_ramp(a0, stop, len(ramp))
