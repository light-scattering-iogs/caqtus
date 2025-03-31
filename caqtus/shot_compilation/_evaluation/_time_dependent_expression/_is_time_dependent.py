import functools
from typing import assert_never

from caqtus_parsing import (
    AST,
    BinaryOperation,
    Call,
    Float,
    Identifier,
    Integer,
    UnaryOperation,
)
from caqtus_parsing import Quantity as QuantityNode


@functools.lru_cache
def is_time_dependent(expression: AST) -> bool:
    match expression:
        case Integer() | Float() | QuantityNode():
            return False
        case Identifier(name):
            return name == "t"
        case BinaryOperation(_, lhs, rhs):
            return is_time_dependent(lhs) or is_time_dependent(rhs)
        case UnaryOperation(_, operand):
            return is_time_dependent(operand)
        case Call():
            return any(is_time_dependent(arg) for arg in expression.args)
        case _:
            assert_never(expression)
