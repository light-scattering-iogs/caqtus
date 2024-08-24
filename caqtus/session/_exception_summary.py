from __future__ import annotations

import traceback
from typing import Optional

import attrs


@attrs.frozen
class TracebackSummary:
    """Represents a summary of an exception and its traceback.

    Attributes:
        exc_type: The fully-qualified name of the exception type, like
            `builtins.RuntimeError`.
        exc_msg: The exception message.
        notes: A list of notes that were attached to the traceback.
        cause: The exception that caused this exception, if any.
        context: The exception that was being handled when this exception was raised,
            if any.
        exceptions: A list of exceptions that were caught by this exception if it is an
            instance of BaseExceptionGroup.
    """

    exc_type: str
    exc_msg: str
    notes: Optional[list[str]]
    cause: Optional[TracebackSummary]
    context: Optional[TracebackSummary]
    exceptions: Optional[list[TracebackSummary]]

    @classmethod
    def from_exception(cls, exc: BaseException) -> TracebackSummary:
        tb = traceback.TracebackException.from_exception(exc)

        cause = cls.from_exception(exc.__cause__) if exc.__cause__ else None
        context = cls.from_exception(exc.__context__) if exc.__context__ else None
        if isinstance(exc, BaseExceptionGroup):
            exceptions = [cls.from_exception(e) for e in exc.exceptions]
        else:
            exceptions = None
        notes = tb.__notes__
        exc_type = type(exc)
        exc_msg = str(exc)

        return cls(
            cause=cause,
            context=context,
            exceptions=exceptions,
            notes=notes,
            exc_type=f"{exc_type.__module__}.{exc_type.__qualname__}",
            exc_msg=exc_msg,
        )
