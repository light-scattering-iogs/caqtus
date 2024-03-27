from collections.abc import Mapping
from typing import Any

from caqtus.types.expression import Expression
from caqtus.types.variable_name import DottedVariableName
from caqtus.types.units.unit_namespace import units


def evaluate_expression(
    expression: Expression,
    namespace: Mapping[DottedVariableName, Any],
    builtins: Mapping[DottedVariableName, Any] = units,
) -> Any:
    """Evaluate an expression in the given namespace.



    Args:
        expression: the expression to evaluate
        namespace: the namespace in which the expression should be evaluated
        builtins: the builtins to use

    Returns:
        The value of the expression
    """

    d = dict(builtins)
    d.update(namespace)

    return expression.evaluate(d)
