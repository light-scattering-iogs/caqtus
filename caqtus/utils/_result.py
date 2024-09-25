from __future__ import annotations

from collections.abc import Callable
from typing import Never, Literal, overload, Any

import attrs
from typing_extensions import TypeIs


@attrs.frozen(repr=False, str=False)
class Success[T]:
    value: T

    def unwrap(self) -> T:
        return self.value

    def map[R](self, func: Callable[[T], R]) -> Success[R]:
        return Success(func(self.value))

    @staticmethod
    def is_success() -> Literal[True]:
        return True

    @staticmethod
    def is_failure() -> Literal[False]:
        return False

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"Success({self.value!r})"


def is_success[T](result: Result[T, Any]) -> TypeIs[Success[T]]:
    return result.is_success()


def is_failure[E](result: Result[Any, E]) -> TypeIs[Failure[E]]:
    return result.is_failure()


def is_failure_type[E](result: Result, error_type: type[E]) -> TypeIs[Failure[E]]:
    return is_failure(result) and isinstance(result._error, error_type)


@attrs.frozen(repr=False, str=False)
class Failure[E]:
    _error: E

    def unwrap(self) -> Never:
        if not isinstance(self._error, Exception):
            raise ValueError("Only exceptions can be unwrapped")
        raise self._error

    def map(self, func: Callable) -> Failure[E]:
        return self

    @staticmethod
    def is_success() -> Literal[False]:
        return False

    @staticmethod
    def is_failure() -> Literal[True]:
        return True

    def __str__(self) -> str:
        return str(self._error)


type Result[T, E] = Success[T] | Failure[E]


@overload
def unwrap[T](value: Success[T]) -> T: ...


@overload
def unwrap(value: Failure[Exception]) -> Never: ...


def unwrap(value):
    if isinstance(value, Success):
        return value.value
    else:
        raise value._error
