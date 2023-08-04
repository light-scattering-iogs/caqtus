import logging
from abc import ABC
from contextlib import AbstractContextManager
from threading import Lock

from .experiment_config_collection import ExperimentConfigCollection
from .sequence_file_system import SequenceFileSystem

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ExperimentSessionNotActiveError(RuntimeError):
    pass


class ExperimentSession(
    AbstractContextManager["ExperimentSession"],
    SequenceFileSystem,
    ExperimentConfigCollection,
    ABC,
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

    def __init__(self, *args, **kwargs):
        self._is_active = False
        self._lock = Lock()

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
