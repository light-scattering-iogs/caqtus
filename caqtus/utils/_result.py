from __future__ import annotations

from collections.abc import Callable
from typing import Never, Literal

import attrs
from typing_extensions import TypeIs


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

    @staticmethod
    def is_failure() -> Literal[False]:
        return False


def is_success[T, E: Exception](result: Result[T, E]) -> TypeIs[Success[T]]:
    return result.is_success()


def is_failure[T, E: Exception](result: Result[T, E]) -> TypeIs[Failure[E]]:
    return result.is_failure()


def is_failure_type[
    E: Exception
](result: Result, error_type: type[E]) -> TypeIs[Failure[E]]:
    return is_failure(result) and isinstance(result.error, error_type)


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

    @staticmethod
    def is_failure() -> Literal[True]:
        return True


type Result[T, E: Exception] = Success[T] | Failure[E]
