from typing import TypeVar, assert_never

from returns.result import Result, Success, Failure

T = TypeVar("T")
E = TypeVar("E", bound=Exception)


def return_or_raise(result: Result[T, E]) -> T:
    match result:
        case Success(value):
            return value
        case Failure(error):
            raise error
        case other:
            assert_never(other)
