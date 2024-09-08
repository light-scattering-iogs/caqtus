from __future__ import annotations

from collections.abc import Callable
from typing import Never, Literal

import attrs


@attrs.frozen
class Success[T]:
    value: T

    def unwrap(self) -> T:
        return self.value

    def map[R](self, func: Callable[[T], R]) -> Success[R]:
        return Success(func(self.value))

    @staticmethod
    def is_success() -> Literal[True]:
        return True


@attrs.frozen
class Failure[E: Exception]:
    error: E

    def unwrap(self) -> Never:
        raise self.error

    def map(self, func: Callable) -> Failure[E]:
        return self

    @staticmethod
    def is_success() -> Literal[False]:
        return False


type Result[T, E: Exception] = Success[T] | Failure[E]
