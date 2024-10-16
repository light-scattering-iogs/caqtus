"""This module defines recoverable exceptions.

These are exceptions that can occur during the normal execution of a program, for
example when the user enters an invalid value, or when a connection to an external
resource fails.

These errors will not crash caqtus applications, but instead will be caught and
displayed to the user, so that they can fix the error and retry the operation.

Exceptions that are not recoverable will not be caught, and are allowed to crash
the applications.

Only make exceptions recoverable if you expect them to happen in normal operation.
"""

from __future__ import annotations

import tblib.pickling_support


def is_recoverable(error: BaseException) -> bool:
    """Check if an error is recoverable.

    An error is recoverable if any of the following conditions are met:

    * The error is an instance of :class:`RecoverableException`.
    * The error's cause is a recoverable error.
    * The error is an instance of :class:`BaseExceptionGroup` and all its
      sub-exceptions are recoverable.

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
) -> (
    tuple[BaseException, BaseException]
    | tuple[None, BaseException]
    | tuple[BaseException, None]
):
    """Split an exception into recoverable and non-recoverable parts.

    This function is mainly meant to split exception groups.

    Returns:
        A tuple of two elements:

        * The recoverable part of the exception, or None if there is no recoverable
          part.
        * The non-recoverable part of the exception, or None if there is no
          non-recoverable part.
    """

    if isinstance(exception, BaseExceptionGroup):
        return exception.split(is_recoverable)  # type: ignore[reportReturnType]
    else:
        if is_recoverable(exception):
            return exception, None
        else:
            return None, exception


class RecoverableException(Exception):  # noqa: N818
    """An error that can be recovered from.

    This is an error that happen when the user does something wrong, and it is possible
    to retry the operation after they fix the error.

    This is a base class for all recoverable errors.
    It should not be raised directly, instead raise a subclass.
    """

    pass


class InvalidTypeError(TypeError, RecoverableException):
    """Raised when a value is not of the expected type.

    This error is raised when a value is not of the expected type, but it is possible
    to recover from the error by changing the value to the correct type.
    """

    pass


class InvalidValueError(ValueError, RecoverableException):
    """Raised when a value is invalid.

    This error is raised when a value is invalid, but it is possible to recover from the
    error by changing the value to a valid one.
    """

    pass


class ConnectionFailedError(ConnectionError, RecoverableException):
    """Raised when a connection to an external resource fails.

    This error is raised when a connection to an external resource fails, but it is
    possible to recover from the error by retrying the connection or fixing the
    connection settings.
    """

    pass


class ShotAttemptsExceededError(RecoverableException, ExceptionGroup):
    """Raised when the number of shot attempts exceeds the maximum allowed."""

    def derive(self, excs):
        return ShotAttemptsExceededError(self.message, excs)


class EvaluationError(RecoverableException):
    """Raised when an error occurs during the evaluation of an expression.

    This error is raised when an error occurs during the evaluation of an expression
    entered by the user.
    The user should fix the expression and retry the operation.
    """

    pass


class NotDefinedUnitError(RecoverableException):
    """Raised when the user tries to use a unit that is not defined."""


tblib.pickling_support.install(
    RecoverableException,
    InvalidTypeError,
    InvalidValueError,
    ConnectionFailedError,
    ShotAttemptsExceededError,
    EvaluationError,
    NotDefinedUnitError,
)
