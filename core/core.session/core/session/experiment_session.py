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

    Implementations of this class manage access to the permanent storage of the experiment.

    An ExperimentSession is a context manager and must be used in a `with` statement. If an error occurs inside the
    `with` block, the session will be rolled back to the state it was in before the `with` block was entered in order to
    prevent leaving the data in an inconsistent state.

    Attributes:
        sequence_hierarchy: Gives access to all sequences stored in the session.
        shot_collection: Gives access to the data acquired while running shots on the experiment.
        experiment_configs: Gives access to the history of the device configurations.
    """

    sequence_hierarchy: SequenceHierarchy
    shot_collection: ShotCollection
    experiment_configs: ExperimentConfigCollection
