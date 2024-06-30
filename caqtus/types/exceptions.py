import tblib.pickling_support


@tblib.pickling_support.install
class RecoverableError(Exception):
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
    """

    if isinstance(error, RecoverableError):
        return True

    if error.__cause__ is not None:
        return is_recoverable(error.__cause__)

    if isinstance(error, BaseExceptionGroup):
        return all(is_recoverable(e) for e in error.exceptions)

    return False
