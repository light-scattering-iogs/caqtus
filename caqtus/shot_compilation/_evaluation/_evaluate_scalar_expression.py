import functools
import operator
from collections.abc import Sequence
from typing import assert_never, Any

from typing_extensions import TypeIs

import caqtus.formatter as fmt
import caqtus_parsing.nodes as nodes
from caqtus.types.expression import Expression
from caqtus.types.parameter import Parameters
from caqtus.types.recoverable_exceptions import EvaluationError, InvalidTypeError
from caqtus.types.units import Quantity, is_scalar_quantity, Unit, DimensionalityError
from caqtus_parsing import parse, InvalidSyntaxError
from ._constants import CONSTANTS
from ._exceptions import (
    UndefinedParameterError,
    InvalidOperationError,
    UndefinedUnitError,
)
from ._functions import SCALAR_FUNCTIONS
from ._scalar import Scalar
from ._units import units


def evaluate_scalar_expression(
    expression: Expression, parameters: Parameters
) -> Scalar:
    """Evaluate a scalar expression.

    Args:
        expression: The expression to evaluate.
        parameters: The parameters to use in the evaluation.

    Returns:
        The result of the evaluation.

    Raises:
        EvaluationError: if an error occurred during evaluation, with the reason for the
            error as the exception cause.
    """

    try:
        ast = parse(str(expression))
        return evaluate_expression(ast, parameters)
    except (EvaluationError, InvalidSyntaxError) as error:
        raise EvaluationError(
            f"Could not evaluate {fmt.expression(expression)}."
        ) from error


def evaluate_bool_expression(
    expression: nodes.Expression, parameters: Parameters
) -> bool:
    value = evaluate_expression(expression, parameters)
    if not isinstance(value, bool):
        raise InvalidTypeError(
            f"Expected {fmt.expression(expression)} to evaluate to a boolean, "
            f"but got {fmt.type_(type(value))}."
        )
    return value


def evaluate_float_expression(
    expression: nodes.Expression, parameters: Parameters
) -> float:
    value = evaluate_expression(expression, parameters)
    try:
        return float(value)
    except DimensionalityError as error:
        raise InvalidOperationError(
            f"Could not convert {fmt.expression(expression)} to a float."
        ) from error


def evaluate_expression(expression: nodes.Expression, parameters: Parameters) -> Scalar:
    match expression:
        case int() | float():
            return expression
        case nodes.Variable() as variable:
            return evaluate_scalar_variable(variable, parameters)
        case (
            nodes.Add()
            | nodes.Subtract()
            | nodes.Multiply()
            | nodes.Divide()
            | nodes.Power() as binary_operator
        ):
            return evaluate_binary_operator(binary_operator, parameters)
        case nodes.Plus() | nodes.Minus() as unary_operator:
            return evaluate_unary_operator(unary_operator, parameters)
        case nodes.Quantity():
            return evaluate_quantity(expression)
        case nodes.Call():
            return evaluate_function_call(expression, parameters)
        case _:  # pragma: no cover
            assert_never(expression)


def evaluate_scalar_variable(
    variable: nodes.Variable, parameters: Parameters
) -> Scalar:
    name = variable.name
    if name in parameters:
        # We can use str as key instead of DottedVariableName because they have the
        # same hash.
        return parameters[name]  # type: ignore[reportArgumentType]
    elif name in CONSTANTS:
        return CONSTANTS[name]
    else:
        raise UndefinedParameterError(f"Parameter {name} is not defined.")


def evaluate_function_call(
    function_call: nodes.Call,
    parameters: Parameters,
) -> Scalar:
    function_name = function_call.function
    try:
        # We can use str as key instead of VariableName because they have the
        # same hash.
        function = SCALAR_FUNCTIONS[function_name]  # type: ignore[reportArgumentType]
    except KeyError:
        raise UndefinedFunctionError(
            f"Function {function_name} is not defined."
        ) from None
    arguments = [
        evaluate_expression(argument, parameters) for argument in function_call.args
    ]
    return function(*arguments)


def evaluate_binary_operator(
    binary_operator: nodes.BinaryOperator,
    parameters: Parameters,
) -> Scalar:
    left = evaluate_expression(binary_operator.left, parameters)
    right = evaluate_expression(binary_operator.right, parameters)
    match binary_operator:
        case nodes.Add():
            result = left + right
        case nodes.Subtract():
            result = left - right
        case nodes.Multiply():
            result = left * right
        case nodes.Divide():
            result = left / right
        case nodes.Power(exponent):
            if not isinstance(right, (int, float)):
                raise InvalidOperationError(
                    f"The exponent {exponent} must be a real number, not {right}."
                )
            result = left**right
        case _:  # pragma: no cover
            assert_never(binary_operator)
    assert is_scalar(result)
    return result


def evaluate_unary_operator(
    unary_operator: nodes.UnaryOperator,
    parameters: Parameters,
) -> Scalar:
    operand = evaluate_expression(unary_operator.operand, parameters)
    match unary_operator:
        case nodes.Plus():
            result = operand
        case nodes.Minus():
            result = -operand
        case _:  # pragma: no cover
            assert_never(unary_operator)
    assert is_scalar(result)
    return result


def evaluate_quantity(quantity: nodes.Quantity) -> Quantity[float]:
    magnitude = quantity.magnitude

    multiplicative_units = evaluate_units(quantity.multiplicative_units)

    if not quantity.divisional_units:
        return Quantity(magnitude, multiplicative_units)
    else:
        divisive_units = evaluate_units(quantity.divisional_units)
        total_units = multiplicative_units / divisive_units
        assert isinstance(total_units, Unit)
        return Quantity(magnitude, total_units)


@functools.lru_cache
def evaluate_units(unit_nodes: Sequence[nodes.UnitTerm]) -> Unit:
    assert unit_nodes
    accumulated_units = []
    for unit_term in unit_nodes:
        try:
            base = units[unit_term.unit]
        except KeyError:
            raise UndefinedUnitError(f"Unit {unit_term.unit} is not defined.") from None
        exponent = unit_term.exponent or 1
        accumulated_units.append(base**exponent)
    return functools.reduce(operator.mul, accumulated_units)


def is_scalar(value: Any) -> TypeIs[Scalar]:
    return isinstance(value, (int, bool, float)) or is_scalar_quantity(value)


class UndefinedFunctionError(EvaluationError):
    pass
