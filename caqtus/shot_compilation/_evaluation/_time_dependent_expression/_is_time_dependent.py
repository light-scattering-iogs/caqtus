from typing import assert_never

from caqtus_parsing import nodes


def is_time_dependent(expression: nodes.Expression) -> bool:
    """Returns True if the expression depends on the variable `t`."""

    match expression:
        case int() | float() | nodes.Quantity():
            return False
        case nodes.Variable(name=name):
            return name == "t"
        case (
            nodes.Add()
            | nodes.Subtract()
            | nodes.Multiply()
            | nodes.Divide()
            | nodes.Power() as binary_operator
        ):
            left_time_dependent = is_time_dependent(binary_operator.left)
            right_time_dependent = is_time_dependent(binary_operator.right)
            return left_time_dependent or right_time_dependent
        case nodes.Plus() | nodes.Minus() as unary_operator:
            return is_time_dependent(unary_operator.expression)
        case nodes.Call():
            return any(is_time_dependent(arg) for arg in expression.args)
        case _:  # pragma: no cover
            assert_never(expression)
