from __future__ import annotations

from collections.abc import Callable
from typing import Never, overload, Any

import attrs
from typing_extensions import TypeIs


@attrs.frozen(repr=False, str=False)
class Success[T]:
    """A successful result containing a value of type T."""

    value: T

    def map[R](self, func: Callable[[T], R]) -> Success[R]:
        return Success(func(self.value))

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"Success({self.value!r})"

    def result(self) -> T:
        return self.value

    def content(self) -> T:
        """Return the wrapped successful value."""

        return self.value


def is_success[T](result: Result[T, Any]) -> TypeIs[Success[T]]:
    """Check if a result is a success."""

    return isinstance(result, Success)


def is_failure[E](result: Result[Any, E]) -> TypeIs[Failure[E]]:
    """Check if a result is a failure."""

    return isinstance(result, Failure)


def is_failure_type[E](result: Result, error_type: type[E]) -> TypeIs[Failure[E]]:
    """Check if a result is a failure and contains a specific error type."""

    return is_failure(result) and isinstance(result._error, error_type)


@attrs.frozen(repr=False, str=False)
class Failure[E]:
    """A failed result containing an error code of type E."""

    _error: E

    def map(self, func: Callable) -> Failure[E]:
        return self

    def __str__(self) -> str:
        return str(self._error)


type Result[T, E] = Success[T] | Failure[E]


@overload
def unwrap[T](value: Success[T]) -> T: ...


@overload
def unwrap(value: Failure[Exception]) -> Never: ...


def unwrap(value):
    """Unwrap a result when the failure case is an exception.

    This function can be used to recover the wrapped value from a Success or raise the
    wrapped exception from a Failure.

    Args:
        value: The result to unwrap.
            If the value is a Failure, its content must be an exception.

    Returns:
        The value wrapped if the argument passes is a Success.

    Raises:
        The exception wrapped if the argument passed is a Failure containing an
        exception.
    """

    if isinstance(value, Success):
        return value.value
    else:
        raise value._error
