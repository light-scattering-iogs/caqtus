from caqtus.types.recoverable_exceptions import EvaluationError


class UndefinedParameterError(EvaluationError):
    """Indicates that a parameter was not defined in an expression."""


class InvalidOperationError(EvaluationError):
    """Indicates that an invalid operation was attempted."""
