import logging
from abc import abstractmethod
from contextlib import AbstractContextManager
from datetime import datetime
from typing import Protocol, Any

from sequence.runtime import Shot
from sql_model import DataType
from .experiment_config_collection import ExperimentConfigCollection
from .sequence_file_system import SequenceFileSystem

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ExperimentSessionNotActiveError(RuntimeError):
    pass


class ShotCollection(Protocol):
    @abstractmethod
    def get_shot_data(self, shot: Shot, data_type: DataType) -> dict[str, Any]:
        """Get the data of a given shot."""

        raise NotImplementedError()

    @abstractmethod
    def add_shot_data(
        self, shot: Shot, data: dict[str, Any], data_type: DataType
    ) -> None:
        """Add data to a given shot."""

        raise NotImplementedError()

    @abstractmethod
    def get_shot_start_time(self, shot: Shot) -> datetime:
        """Get the start time of a given shot."""

        raise NotImplementedError()

    @abstractmethod
    def get_shot_end_time(self, shot: Shot) -> datetime:
        """Get the end time of a given shot."""

        raise NotImplementedError()


class ExperimentSession(
    AbstractContextManager["ExperimentSession"],
    SequenceFileSystem,
    ExperimentConfigCollection,
    Protocol,
):
    """Manage the experiment session.

    Instances of this class manage access to the permanent storage of the experiment.
    A session contains the history of the experiment configuration and the current
    configuration. It also contains the sequence tree of the experiment, with the
    sequence states and data.

    Some objects in the sequence.runtime package (Sequence, Shot) that can read and
    write to the experiment data storage have methods that require an activated
    ExperimentSession.

    If an error occurs within an activated session block, the session state is
    automatically rolled back to the beginning of the activation block. This prevents
    leaving some data in an inconsistent state.
    """

    shot_collection: ShotCollection

    def activate(self):
        """Activate the session

        This method is meant to be used in a with statement.

        Example:
            # Ok
            with session.activate():
                config = session.get_current_experiment_config()

            # Not ok
            config = session.get_current_experiment_config()

            # Not ok
            session.activate()
            config = session.get_current_experiment_config()
        """

        return self
