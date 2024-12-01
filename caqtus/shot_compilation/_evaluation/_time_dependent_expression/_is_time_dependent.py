import functools
from typing import assert_never

import caqtus_parsing.nodes as nodes


@functools.lru_cache
def is_time_dependent(expression: nodes.Expression) -> bool:
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
            return is_time_dependent(binary_operator.left) or is_time_dependent(
                binary_operator.right
            )
        case nodes.Plus() | nodes.Minus() as unary_operator:
            return is_time_dependent(unary_operator.operand)
        case nodes.Call():
            return any(is_time_dependent(arg) for arg in expression.args)
        case _:
            assert_never(expression)
