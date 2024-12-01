from typing import assert_never

import numpy as np

import caqtus.formatter as fmt
import caqtus_parsing.nodes as nodes
from caqtus.types.expression import Expression
from caqtus.types.parameter import Parameters
from caqtus.types.recoverable_exceptions import EvaluationError, InvalidValueError
from caqtus.types.units import dimensionless, InvalidDimensionalityError
from caqtus_parsing import parse, InvalidSyntaxError
from ._analog_expression import AnalogInstruction, evaluate_analog_ast
from ._is_time_dependent import is_time_dependent
from .._evaluate_scalar_expression import (
    evaluate_bool_expression,
    evaluate_float_expression,
)
from ...timed_instructions import TimedInstruction, Pattern
from ...timing import Time, number_ticks

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
    except (EvaluationError, InvalidSyntaxError) as error:
        raise EvaluationError(
            f"Could not evaluate {fmt.expression(expression)}."
        ) from error


def evaluate_digital_expression(
    expression: nodes.Expression,
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
        case int() | float() | nodes.Quantity():
            raise AssertionError(
                "This should never happen, because at this point, the expression "
                "is known to be time-dependent."
            )
        case nodes.Variable(name=name):
            assert name == "t"
            raise InvalidOperationError(
                f"{fmt.expression(expression)} is not a valid digital expression."
            )
        case (
            nodes.Add()
            | nodes.Subtract()
            | nodes.Multiply()
            | nodes.Divide()
            | nodes.Power()
            | nodes.Plus()
            | nodes.Minus()
        ):
            raise InvalidOperationError(
                f"{fmt.expression(expression)} is not a valid digital expression."
            )
        case nodes.Call():
            return evaluate_call(expression, parameters, t1, t2, timestep)
        case _:
            assert_never(expression)


def evaluate_call(
    call: nodes.Call,
    parameters: Parameters,
    t1: Time,
    t2: Time,
    timestep: Time,
) -> DigitalInstruction:
    if call.function == "square_wave":
        if len(call.args) == 0:
            raise InvalidOperationError(
                f"Function {call.function} requires at least 1 argument, got 0."
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
                f"Function {call.function} takes at most 2 arguments, got "
                f"{len(call.args)}."
            )
        x_instr = evaluate_analog_ast(x_expression, parameters, t1, t2, timestep)
        if x_instr.units != dimensionless:
            raise InvalidDimensionalityError(
                f"{fmt.expression(x_expression)} in 'square_wave' must be "
                f"dimensionless, got {x_instr.units}."
            )
        return evaluate_square_wave(x_instr, duty_cycle)
    else:
        raise InvalidOperationError(
            f"Function {call.function} is not supported in digital expressions."
        )


def evaluate_square_wave(
    x_instr: AnalogInstruction, duty_cycle: float
) -> DigitalInstruction:
    raise NotImplementedError


class InvalidOperationError(EvaluationError):
    """Raised when an invalid operation is attempted."""

    pass
