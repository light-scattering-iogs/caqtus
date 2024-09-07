from __future__ import annotations

from collections.abc import Callable
from typing import Never

import attrs


@attrs.frozen
class Success[T]:
    value: T

    def unwrap(self) -> T:
        return self.value

    def map[R](self, func: Callable[[T], R]) -> Success[R]:
        return Success(func(self.value))


@attrs.frozen
class Failure[E: Exception]:
    error: E

    def unwrap(self) -> Never:
        raise self.error

    def map(self, func: Callable) -> Failure[E]:
        return self


type Result[T, E: Exception] = Success[T] | Failure[E]
