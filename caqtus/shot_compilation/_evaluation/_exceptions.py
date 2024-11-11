from caqtus.types.recoverable_exceptions import InvalidValueError, RecoverableException


class EvaluationError(RecoverableException):
    """An error that occurred while evaluating an expression."""


class UndefinedParameterError(EvaluationError):
    """Indicates that a parameter was not defined in an expression."""


class InvalidOperationError(EvaluationError):
    """Indicates that an invalid operation was attempted."""
