from typing import Protocol

from .experiment_session import ExperimentSession


class ExperimentSessionMaker(Protocol):
    """Used to create a new experiment session with predefined parameters."""

    def __call__(self) -> ExperimentSession:
        ...
