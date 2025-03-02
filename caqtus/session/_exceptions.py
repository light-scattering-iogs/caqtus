from __future__ import annotations

from caqtus.session import PathError


class PathIsSequenceError(PathError):
    """Raised when a path is expected to be a sequence, but it is not."""

    pass


class PathIsNotSequenceError(PathError):
    """Raised when a path is expected to not be a sequence, but it is."""

    pass


class DataNotFoundError(RuntimeError):
    """Raised when data is not found in a shot."""

    pass


class SequenceStateError(RuntimeError):
    """Raised when an invalid sequence state is encountered.

    This error is raised when trying to perform an operation that is not allowed in the
    current state, such as adding data to a sequence that is not in the RUNNING state.
    """

    pass


class SequenceRunningError(SequenceStateError):
    """Raised when trying to perform an invalid operation on a running sequence."""

    pass


class SequenceNotRunningError(SequenceStateError):
    """Raised when trying to perform an invalid operation on a non-running sequence."""

    pass


class InvalidStateTransitionError(SequenceStateError):
    """Raised when an invalid state transition is attempted.

    This error is raised when trying to transition a sequence to an invalid state.
    """

    pass


class SequenceNotEditableError(SequenceStateError):
    """Raised when trying to edit a sequence that is not in the draft state."""

    pass


class SequenceNotLaunchedError(SequenceStateError):
    """Raised when accessing information only available after launching a sequence."""

    pass


class SequenceNotCrashedError(SequenceStateError):
    """Raised when trying to read the exceptions of a sequence that is not crashed."""

    pass


class ShotNotFoundError(RuntimeError):
    """Raised when a shot is not found in a sequence."""

    pass
