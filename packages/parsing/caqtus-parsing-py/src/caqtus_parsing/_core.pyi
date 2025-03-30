from __future__ import annotations

class ParseNode:
    class Integer(ParseNode):
        def __init__(self, value: int) -> None: ...

        __match_args__ = ("value",)
        @property
        def value(self) -> int: ...

    class Float(ParseNode):
        def __init__(self, value: float) -> None: ...

        __match_args__ = ("value",)
        @property
        def value(self) -> float: ...

    class Quantity(ParseNode):
        def __init__(self, value: float, unit: str) -> None: ...

        __match_args__ = ("value", "unit")
        @property
        def value(self) -> float: ...
        @property
        def unit(self) -> str: ...

    class Identifier(ParseNode):
        def __init__(self, name: str) -> None: ...

        __match_args__ = ("name",)
        @property
        def name(self) -> str: ...

type AST = (
    ParseNode.Integer | ParseNode.Float | ParseNode.Quantity | ParseNode.Identifier
)

def parse(string: str) -> AST: ...
