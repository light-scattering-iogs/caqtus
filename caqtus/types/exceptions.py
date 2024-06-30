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

    Note that if an error can be recoverable even if its cause is not recoverable, if
    the error itself is recoverable.
    """

    if isinstance(error, RecoverableException):
        return True

    if error.__cause__ is not None:
        return is_recoverable(error.__cause__)

    if isinstance(error, BaseExceptionGroup):
        return all(is_recoverable(e) for e in error.exceptions)

    return False


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
