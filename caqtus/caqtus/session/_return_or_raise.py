from typing import TypeVar, assert_never

from returns.result import Result, Success, Failure

T = TypeVar("T")
E = TypeVar("E", bound=Exception)


def unwrap(result: Result[T, E]) -> T:
    match result:
        case Success(value):
            return value
        case Failure(error):
            raise error
        case other:
            assert_never(other)


def is_success(result: Result[T, E]) -> bool:
    match result:
        case Success(_):
            return True
        case Failure(_):
            return False
        case other:
            assert_never(other)
