from __future__ import annotations

import logging
from contextlib import AbstractContextManager
from typing import Protocol

from core.session.parameter_namespace import ParameterNamespace

from .device_configuration_collection import DeviceConfigurationCollection
from .path_hierarchy import PathHierarchy
from .sequence_collection import SequenceCollection

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ExperimentSessionNotActiveError(RuntimeError):
    pass


class ExperimentSession(
    AbstractContextManager,
    Protocol,
):
    """Provides a connection to access the permanent storage of the experiment.

    An :py:class:`ExperimentSession` object allows to read and write configurations
    and data of the experiment.
    Every function and method that read or write data do so through an experiment
    session object.

    A session contains the following data:
    - A hierarchy of paths.
    - A collection of sequences.
    - A default collection of device configurations used to run a sequence.
    - A collection of global parameters.
    Global parameters are parameters that are not specific to a sequence, but are
    relevant for all the sequences.


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
    :py:class:`core.session.ExperimentSessionMaker`.
    """

    paths: PathHierarchy
    sequences: SequenceCollection
    default_device_configurations: DeviceConfigurationCollection

    def get_global_parameters(self) -> ParameterNamespace:
        """Returns a copy of the global parameters of the session."""

        ...

    def set_global_parameters(self, parameters: ParameterNamespace) -> None:
        """Overwrite the global parameters of the session with the given parameters."""

        ...
