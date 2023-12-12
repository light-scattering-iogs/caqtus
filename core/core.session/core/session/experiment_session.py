import logging
from contextlib import AbstractContextManager
from typing import Protocol

from .experiment_config_collection import ExperimentConfigCollection
from .sequence_file_system import SequenceHierarchy
from .shot_collection import ShotCollection

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ExperimentSessionNotActiveError(RuntimeError):
    pass


class ExperimentSession(
    AbstractContextManager["ExperimentSession"],
    Protocol,
):
    """Interface that define an experiment session.

    Implementations of this class manage access to the permanent storage of the experiment. It is possible to create
    several implementations of this class that use different storage backends. For example, one implementation could
    use a SQL database while another could use a local file system.

    A session contains a hierarchy of sequences with their associated shots. It also contains the history of the
    experiment configurations.

    An ExperimentSession must also be a context manager. This means that it must be used in a with statement. If an
    error occurs inside the with block, the session must be rolled back to the state it was in before the with block.
    This requirement is necessary to prevent leaving the data in an inconsistent state.

    All object that need to read or write to the permanent storage of the experiment must do so through an
    ExperimentSession.

    Attributes:
        sequence_hierarchy: This is a file-system-like object that can be used to create, delete and check for the
            existence of sequences.
        shot_collection: This is an object that allows to access the shots and their associated data.
    """

    sequence_hierarchy: SequenceHierarchy
    shot_collection: ShotCollection
    experiment_configs: ExperimentConfigCollection

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
