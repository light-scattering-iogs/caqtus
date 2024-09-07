from __future__ import annotations

from collections.abc import Callable
from typing import Never

import attrs


@attrs.frozen
class _Success[T]:
    value: T

    def unwrap(self) -> T:
        return self.value

    def map[R](self, func: Callable[[T], R]) -> _Success[R]:
        return _Success(func(self.value))


@attrs.frozen
class _Failure[E: Exception]:
    error: E

    def unwrap(self) -> Never:
        raise self.error

    def map(self, func: Callable) -> _Failure[E]:
        return self


type _Result[T, E: Exception] = _Success[T] | _Failure[E]
