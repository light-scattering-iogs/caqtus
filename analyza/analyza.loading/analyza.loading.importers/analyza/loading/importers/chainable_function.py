from abc import ABC
from typing import (
    Callable,
    Generic,
    TypeVar,
    ParamSpec,
)

P = ParamSpec("P")
S = TypeVar("S")
T = TypeVar("T")

K = TypeVar("K")
V = TypeVar("V")


class ChainableFunction(Generic[P, T], ABC):
    def __init__(self, func: Callable[P, T]):
        self._func = func

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        return self._func(*args, **kwargs)

    def __or__(self, other: "ChainableFunction[[T], S]") -> "ChainableFunction[P, S]":
        def _chain(*args: P.args, **kwargs: P.kwargs) -> S:
            return other(self(*args, **kwargs))

        if isinstance(other, ChainableFunction):
            return ChainableFunction(_chain)
        else:
            return NotImplemented
