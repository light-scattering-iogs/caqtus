from __future__ import annotations

import logging
from contextlib import AbstractContextManager
from typing import Protocol, TYPE_CHECKING

from caqtus.types.parameter import ParameterNamespace
from ._device_configuration_collection import DeviceConfigurationCollection
from ._path import PureSequencePath
from ._path_hierarchy import PathHierarchy
from ._sequence_collection import SequenceCollection

if TYPE_CHECKING:
    from ._sequence import Sequence

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ExperimentSessionNotActiveError(RuntimeError):
    pass


class ExperimentSession(
    AbstractContextManager,
    Protocol,
):
    """Provides a transactional connection to the storage of the experiment.

    An :py:class:`ExperimentSession` object allows to read and write configurations
    and data of the experiment.
    Every function and method that read or write data do so through an experiment
    session object.

    An experiment session object must be activated before it can be used.
    This is done by using the `with` statement on the session, inside which the session
    is active.
    If an error occurs inside the `with` block of the session, the data will be
    rolled back to the state it was in before the `with` block was entered in order to
    prevent leaving the storage in an inconsistent state.
    Data is only committed to the permanent storage when the `with` block is exited and
    will only be visible to other sessions after that point.
    For this reason, it is recommended to keep the `with` block as short as possible.

    A given session is not meant to be used concurrently.
    It can't be pickled and must not be passed to other processes.
    It is also not thread safe.
    It is not meant to be used by several coroutines at the same time, even if they
    belong to the same thread.

    It is possible to create multiple sessions connecting to the same storage using an
    :py:class:`caqtus.session.ExperimentSessionMaker`.
    """

    @property
    def paths(self) -> PathHierarchy:
        """The hierarchy of paths in the experiment session."""

        ...

    @property
    def sequences(self) -> SequenceCollection:
        """The collection of sequences in the experiment session."""

        ...

    default_device_configurations: DeviceConfigurationCollection
    """The default device configurations used to run a sequence."""

    def get_sequence(self, path: PureSequencePath | str) -> Sequence:
        """Get a sequence object from the session.

        Args:
            path: The path of the sequence to get.

        Returns:
            The sequence object.

        Raises:
            SequenceNotFoundError: If the sequence does not exist.
        """

        from ._sequence import Sequence

        return Sequence(path, self)

    def get_global_parameters(self) -> ParameterNamespace:
        """Returns a copy of the global parameters of the session.

        Global parameters are parameters that are not specific to a sequence, but are
        relevant for all the sequences.
        """

        ...

    def set_global_parameters(self, parameters: ParameterNamespace) -> None:
        """Overwrite the global parameters of the session with the given parameters."""

        ...
