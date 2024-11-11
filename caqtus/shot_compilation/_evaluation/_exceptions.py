from caqtus.types.recoverable_exceptions import InvalidValueError, RecoverableException


class EvaluationError(RecoverableException):
    """An error that occurred while evaluating an expression."""


class UndefinedParameterError(InvalidValueError):
    """Indicates that a parameter was not defined in an expression."""
