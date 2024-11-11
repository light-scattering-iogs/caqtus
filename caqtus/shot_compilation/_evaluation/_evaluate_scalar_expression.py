from collections.abc import Mapping
from typing import assert_never

import caqtus_parsing.nodes as nodes
from caqtus.types.expression import Expression
from caqtus.types.parameter import Parameter
from caqtus.types.units import Quantity
from caqtus.types.variable_name import DottedVariableName
from caqtus_parsing import parse

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
    return evaluate_expression(ast)


def evaluate_expression(expression: nodes.Expression) -> Scalar:
    match expression:
        case int() | float():
            return expression
        case _:  # pragma: no cover
            assert_never(expression)
