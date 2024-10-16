"""Defines the result type and its variants: success and failure.

The result type is a union type of :class:`Success` and :class:`Failure` respectively
containing a successful value or an error code.

It is mostly meant to be used as a return type for functions that can fail, but where
we want to be sure to handle all cases in the calling code and not raise unhandled
exceptions.

With a type checker, we can ensure that all possible success and failure cases are
dealt with.

Example:
    .. code-block:: python

        from typing import assert_never

        from caqtus.utils.result import Success, Failure, is_success, is_failure_type

        def read_file(path) -> Success[str] | Failure[FileNotFoundError]:
            try:
                with open(path) as file:
                    return Success(file.read())
            except FileNotFoundError as error:
                return Failure(error)

        result = read_file("file.txt")
        if is_failure_type(result, FileNotFoundError):
            print("File not found")
        elif is_success(result):
            print(result.content())
        else:
            assert_never(result)
"""

from ._result import (
    Failure,
    Success,
    is_failure,
    is_failure_type,
    is_success,
    unwrap,
)

__all__ = [
    "Failure",
    "Success",
    "is_failure",
    "is_failure_type",
    "is_success",
    "unwrap",
]
