from collections.abc import Mapping
from typing import assert_never, Any

from typing_extensions import TypeIs

import caqtus_parsing.nodes as nodes
from caqtus.types.expression import Expression
from caqtus.types.parameter import Parameter
from caqtus.types.units import Quantity, is_scalar_quantity
from caqtus.types.variable_name import DottedVariableName
from caqtus_parsing import parse
from ._constants import CONSTANTS
from ._exceptions import UndefinedParameterError

type Scalar = int | bool | float | Quantity[float]


def evaluate_scalar_expression(
    expression: Expression, parameters: Mapping[DottedVariableName, Parameter]
) -> Scalar:
    """Evaluate a scalar expression.

    Args:
        expression: The expression to evaluate.
        parameters: The parameters to use in the evaluation.

    Returns:
        The result of the evaluation.
    """

    ast = parse(str(expression))
    return evaluate_expression(ast, parameters)


def evaluate_expression(
    expression: nodes.Expression, parameters: Mapping[DottedVariableName, Parameter]
) -> Scalar:
    match expression:
        case int() | float():
            return expression
        case nodes.Variable() as variable:
            return evaluate_scalar_variable(variable, parameters)
        case (
            nodes.Add()
            | nodes.Subtract()
            | nodes.Multiply()
            | nodes.Divide() as binary_operator
        ):
            return evaluate_binary_operator(binary_operator, parameters)
        case _:  # pragma: no cover
            assert_never(expression)


def evaluate_scalar_variable(
    variable: nodes.Variable, parameters: Mapping[DottedVariableName, Parameter]
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


def evaluate_binary_operator(
    binary_operator: nodes.BinaryOperator,
    parameters: Mapping[DottedVariableName, Parameter],
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
        case _:  # pragma: no cover
            assert_never(binary_operator)
    if not is_scalar(result):
        raise AssertionError("Adding two scalars should result in a scalar.")
    return result


def is_scalar(value: Any) -> TypeIs[Scalar]:
    return isinstance(value, (int, bool, float)) or is_scalar_quantity(value)
