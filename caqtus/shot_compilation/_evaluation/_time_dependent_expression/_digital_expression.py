import functools
from typing import assert_never

import numpy as np
from caqtus_parsing import (
    AST,
    BinaryOperation,
    BinaryOperator,
    Float,
    Identifier,
    Integer,
    parse,
    Call,
    UnaryOperator,
    UnaryOperation,
)
from caqtus_parsing import Quantity as QuantityNode

import caqtus.formatter as fmt
from caqtus.types.expression import Expression
from caqtus.types.parameter import Parameters
from caqtus.types.recoverable_exceptions import EvaluationError, InvalidValueError
from caqtus.types.units import InvalidDimensionalityError, dimensionless

from ...timed_instructions import (
    Concatenated,
    Pattern,
    Ramp,
    Repeated,
    TimedInstruction,
    concatenate,
)
from ...timing import Time, number_ticks
from .._evaluate_scalar_expression import (
    evaluate_bool_expression,
    evaluate_float_expression,
)
from ._analog_expression import evaluate_analog_ast
from ._is_time_dependent import is_time_dependent

type DigitalInstruction = TimedInstruction[np.bool]


def evaluate_time_dependent_digital_expression(
    expression: Expression, parameters: Parameters, t1: Time, t2: Time, timestep: Time
) -> DigitalInstruction:
    """Evaluate a time-dependent digital expression.

    Args:
        expression: The expression to evaluate.
        parameters: The parameters to use in the evaluation.
        t1: The start time of the evaluation.
        t2: The end time of the evaluation.
        timestep: The time step of the evaluation.

    Returns:
        The result of the evaluation.

    Raises:
        EvaluationError: if an error occurred during evaluation, with the reason for the
            error as the exception cause.
    """

    try:
        ast = parse(str(expression))
        return evaluate_digital_expression(ast, parameters, t1, t2, timestep)
    except (EvaluationError, SyntaxError) as error:
        raise EvaluationError(
            f"Could not evaluate {fmt.expression(expression)}."
        ) from error


def evaluate_digital_expression(
    expression: AST,
    parameters: Parameters,
    t1: Time,
    t2: Time,
    timestep: Time,
) -> DigitalInstruction:
    if not is_time_dependent(expression):
        value = evaluate_bool_expression(expression, parameters)
        length = number_ticks(t1, t2, timestep)
        return Pattern([value]) * length

    match expression:
        case Integer() | Float() | QuantityNode():
            raise AssertionError(
                "This should never happen, because at this point, the expression "
                "is known to be time-dependent."
            )
        case Identifier(name):
            assert name == "t"
            raise InvalidOperationError(
                f"{fmt.expression(expression)} is not a valid digital expression."
            )
        case BinaryOperation(
            BinaryOperator.Plus
            | BinaryOperator.Minus
            | BinaryOperator.Times
            | BinaryOperator.Div
            | BinaryOperator.Pow,
            _,
            _,
        ):
            raise InvalidOperationError(
                f"{fmt.expression(expression)} is not a valid digital expression."
            )
        case UnaryOperation(UnaryOperator.Neg):
            raise InvalidOperationError(
                f"{fmt.expression(expression)} is not a valid digital expression."
            )
        case Call():
            return evaluate_call(expression, parameters, t1, t2, timestep)
        case _:
            assert_never(expression)


def evaluate_call(
    call: Call,
    parameters: Parameters,
    t1: Time,
    t2: Time,
    timestep: Time,
) -> DigitalInstruction:
    if call.name == "square_wave":
        if len(call.args) == 0:
            raise InvalidOperationError(
                f"Function {call.name} requires at least 1 argument, got 0."
            )
        if len(call.args) == 1:
            x_expression = call.args[0]
            duty_cycle = 0.5
        elif len(call.args) == 2:
            x_expression = call.args[0]
            duty_cycle_expression = call.args[1]
            duty_cycle = evaluate_float_expression(duty_cycle_expression, parameters)
            if not 0 <= duty_cycle <= 1:
                raise InvalidValueError(
                    f"Duty cycle {fmt.expression(duty_cycle_expression)} in "
                    f"'square_wave' must be between 0 and 1, got {duty_cycle}."
                )
        else:
            raise InvalidOperationError(
                f"Function {call.name} takes at most 2 arguments, got "
                f"{len(call.args)}."
            )
        x_instr = evaluate_analog_ast(x_expression, parameters, t1, t2, timestep)
        if x_instr.units != dimensionless:
            raise InvalidDimensionalityError(
                f"{fmt.expression(x_expression)} in 'square_wave' must be "
                f"dimensionless, got {x_instr.units}."
            )
        return square_wave(x_instr.magnitudes, duty_cycle)
    else:
        raise InvalidOperationError(
            f"Function {call.name} is not supported in digital expressions."
        )


@functools.singledispatch
def square_wave(x_instr, duty_cycle: float) -> DigitalInstruction:
    raise NotImplementedError(f"Square wave of {type(x_instr)} is not supported.")


@square_wave.register(Pattern)
def square_wave_pattern(
    x_instr: Pattern[np.float64], duty_cycle: float
) -> DigitalInstruction:
    x_values = x_instr.array
    y_values = np.where(x_values % 1 < duty_cycle, True, False)

    return Pattern.create_without_copy(y_values)


@square_wave.register(Concatenated)
def square_wave_concatenated(
    x_instr: Concatenated[np.float64], duty_cycle: float
) -> DigitalInstruction:
    return concatenate(
        *(square_wave(instr, duty_cycle) for instr in x_instr.instructions)
    )


@square_wave.register(Repeated)
def square_wave_repeated(
    x_instr: Repeated[np.float64], duty_cycle: float
) -> DigitalInstruction:
    return x_instr.repetitions * square_wave(x_instr.instruction, duty_cycle)


@square_wave.register(Ramp)
def square_wave_ramp(
    x_instr: Ramp[np.float64], duty_cycle: float
) -> DigitalInstruction:
    # This implementation of square_wave is not totally correct, because it
    # assumes that the resulting values are repetitions of a single pulse.
    # This is not exactly true, when the bounds of the pulse don't always align
    # on the same clock ticks.
    # I am not sure how to handle the more general case.

    slope = (x_instr.stop - x_instr.start) / len(x_instr)
    period = 1 / slope  # period is in clock ticks

    if period < 2:
        raise InvalidValueError(
            "Period of ramp in 'square_wave' must be at least two clock ticks"
        )

    rounded_period = round(period)
    high_duration = round(duty_cycle * rounded_period)
    low_duration = rounded_period - high_duration
    if high_duration == 0 and duty_cycle != 0:
        raise InvalidValueError(
            "High duration of square wave in smaller than one clock tick"
        )
    if low_duration == 0 and duty_cycle != 1:
        raise InvalidValueError(
            "Low duration of square wave in smaller than one clock tick"
        )

    pulse = Pattern([True]) * high_duration + Pattern([False]) * low_duration
    initial_x = x_instr.start % 1

    cut = round(initial_x * period)
    pulse = pulse[cut:] + pulse[:cut]

    repetitions, remainder = divmod(len(x_instr), rounded_period)
    return pulse * repetitions + pulse[:remainder]


class InvalidOperationError(EvaluationError):
    """Raised when an invalid operation is attempted."""

    pass
