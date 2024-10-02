"""Defines the result type and its variants: success and failure.

The Result type is a union type of Success and Failure, where Success contains a
successful value and Failure contains an error code.

It is mostly meant to be used as a return type for functions that can fail, but were
we want to be sure to handle all cases in the calling code and not raise unhandled
exceptions.

With a type checker, we can ensure that all possible success and failure cases are
dealt with.

Example:
    .. code-block:: python

        from typing import assert_never

        from caqtus.utils._result import Success, Failure

        def read_file(file_path: str) -> Success[str] | Failure[FileNotFoundError]:
            try:
                with open(file_path) as file:
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
    Result,
    Success,
    is_failure,
    is_failure_type,
    is_success,
    unwrap,
)

__all__ = [
    "Failure",
    "Result",
    "Success",
    "is_failure",
    "is_failure_type",
    "is_success",
    "unwrap",
]
