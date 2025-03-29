from __future__ import annotations


class AST:
    class Integer:
        def __init__(self, value: int) -> None: ...
        
        __match_args__ = ("value",)
        @property
        def value(self) -> int: ...


def parse(string: str) -> AST.Integer: ...
