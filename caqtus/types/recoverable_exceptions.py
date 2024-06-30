from __future__ import annotations

from typing import Optional

import tblib.pickling_support


@tblib.pickling_support.install
class RecoverableException(Exception):
    """An error that can be recovered from.

    This is an error that happen when the user does something wrong, and it is possible
    to retry the operation after they fixe the error.

    This is a base class for all recoverable errors.
    It should not be raised directly, instead raise a subclass.
    """

    pass


def is_recoverable(error: BaseException) -> bool:
    """Check if an error is recoverable.

    An error is recoverable if any of the following conditions are met:
    - The error is an instance of RecoverableError.
    - The error was caused by a recoverable error.
    - The error is a group containing only recoverable errors.

    Note that an error can be recoverable even if its cause is not recoverable, if
    the error itself is recoverable.
    """

    if isinstance(error, RecoverableException):
        return True

    if error.__cause__ is not None:
        return is_recoverable(error.__cause__)

    if isinstance(error, BaseExceptionGroup):
        return all(is_recoverable(e) for e in error.exceptions)

    return False


def split_recoverable(
    exception: BaseException,
) -> tuple[Optional[BaseException], Optional[BaseException]]:
    """Split an exception into recoverable and non-recoverable parts."""

    if isinstance(exception, BaseExceptionGroup):
        return exception.split(is_recoverable)
    else:
        if is_recoverable(exception):
            return exception, None
        else:
            return None, exception


@tblib.pickling_support.install
class InvalidTypeError(TypeError, RecoverableException):
    """Raised when a value is not of the expected type.

    This error is raised when a value is not of the expected type, but it is possible
    to recover from the error by changing the value to the correct type.
    """

    pass


@tblib.pickling_support.install
class InvalidValueError(ValueError, RecoverableException):
    """Raised when a value is invalid.

    This error is raised when a value is invalid, but it is possible to recover from the
    error by changing the value to a valid one.
    """

    pass


@tblib.pickling_support.install
class ConnectionFailedError(ConnectionError, RecoverableException):
    """Raised when a connection to an external resource fails.

    This error is raised when a connection to an external resource fails, but it is
    possible to recover from the error by retrying the connection or fixing the
    connection settings.
    """

    pass


@tblib.pickling_support.install
class ShotAttemptsExceededError(RecoverableException, ExceptionGroup):
    """Raised when the number of shot attempts exceeds the maximum.

    This error is raised when the number of shot attempts exceeds the maximum.
    """

    pass


class SequenceInterruptedException(RecoverableException):
    """Raised when a sequence is interrupted by the user before it finishes."""

    pass
