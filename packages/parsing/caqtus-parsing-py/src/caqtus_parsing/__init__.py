from typing import TypeAlias

from caqtus_parsing._core import (
    BinaryOperator,
    ParseNode,
    UnaryOperator,
    parse,
)

Integer = ParseNode.Integer
Float = ParseNode.Float
Quantity = ParseNode.Quantity
Identifier = ParseNode.Identifier
BinaryOperation = ParseNode.BinaryOperation
UnaryOperation = ParseNode.UnaryOperation
Plus = BinaryOperator.Plus
Minus = BinaryOperator.Minus
Times = BinaryOperator.Times
Div = BinaryOperator.Div
Pow = BinaryOperator.Pow
Call = ParseNode.Call

AST: TypeAlias = (
    Integer | Float | Quantity | Identifier | UnaryOperation | BinaryOperation | Call
)


__all__ = [
    "parse",
    "Integer",
    "Float",
    "Quantity",
    "Identifier",
    "UnaryOperation",
    "BinaryOperation",
    "BinaryOperator",
    "UnaryOperator",
    "Plus",
    "Minus",
    "Times",
    "Div",
    "Pow",
    "Call",
    "AST",
]
