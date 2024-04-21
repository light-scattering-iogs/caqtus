from typing import Protocol

from .async_session import AsyncExperimentSession
from .experiment_session import ExperimentSession


class ExperimentSessionMaker(Protocol):
    """Used to create a new experiment session with predefined parameters."""

    def __call__(self) -> ExperimentSession:
        """Create a new experiment session."""
        ...

    def async_session(self) -> AsyncExperimentSession: ...
