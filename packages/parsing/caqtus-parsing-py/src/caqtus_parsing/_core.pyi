from __future__ import annotations

import enum

class UnaryOperator(enum.Enum):
    Neg = ...

class BinaryOperator(enum.Enum):
    Plus = ...
    Minus = ...
    Times = ...
    Div = ...
    Pow = ...

class ParseNode:
    class Integer:
        def __init__(self, value: int) -> None: ...

        __match_args__ = ("value",)
        @property
        def value(self) -> int: ...

    class Float:
        def __init__(self, value: float) -> None: ...

        __match_args__ = ("value",)
        @property
        def value(self) -> float: ...

    class Quantity:
        def __init__(self, value: float, unit: str) -> None: ...

        __match_args__ = ("value", "unit")
        @property
        def value(self) -> float: ...
        @property
        def unit(self) -> str: ...

    class Identifier:
        def __init__(self, name: str) -> None: ...

        __match_args__ = ("name",)
        @property
        def name(self) -> str: ...

    class UnaryOperation:
        def __init__(self, operator: UnaryOperator, operand: AST) -> None: ...

        __match_args__ = ("operator", "operand")
        @property
        def operator(self) -> UnaryOperator: ...
        @property
        def operand(self) -> AST: ...

    class BinaryOperation:
        def __init__(self, operator: BinaryOperator, lhs: AST, rhs: AST) -> None: ...

        __match_args__ = ("operator", "lhs", "rhs")
        @property
        def operator(self) -> BinaryOperator: ...
        @property
        def lhs(self) -> AST: ...
        @property
        def rhs(self) -> AST: ...

    class Call:
        def __init__(self, name: str, args: list[AST]) -> None: ...

        __match_args__ = ("name", "args")
        @property
        def name(self) -> str: ...
        @property
        def args(self) -> list[AST]: ...

type AST = (
    ParseNode.Integer
    | ParseNode.Float
    | ParseNode.Quantity
    | ParseNode.Identifier
    | ParseNode.BinaryOperation
    | ParseNode.UnaryOperation
    | ParseNode.Call
)

def parse(
    string: str,
) -> AST: ...
