import abc
from typing import Protocol

from ._experiment_session import ExperimentSession
from .async_session import AsyncExperimentSession


class StorageManager(Protocol):
    """Used to create a new experiment sessions."""

    @abc.abstractmethod
    def __call__(self) -> ExperimentSession:
        """Create a new experiment session."""

        raise NotImplementedError

    def session(self) -> ExperimentSession:
        """Create a new experiment session."""

        return self()

    @abc.abstractmethod
    def async_session(self) -> AsyncExperimentSession:
        """Create a new asynchronous experiment session."""

        raise NotImplementedError


# Deprecated alias to StorageManager
ExperimentSessionMaker = StorageManager
