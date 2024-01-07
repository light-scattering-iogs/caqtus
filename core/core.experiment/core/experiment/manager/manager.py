from __future__ import annotations

import abc
import concurrent.futures
import threading
import time
import uuid
from collections.abc import Set
from contextlib import AbstractContextManager
from typing import Optional

from core.session import ExperimentSessionMaker, PureSequencePath


class ExperimentManager(abc.ABC):
    @abc.abstractmethod
    def create_procedure(self, procedure_name: str) -> Procedure:
        raise NotImplementedError


class Procedure(AbstractContextManager, abc.ABC):
    """Used to perform a procedure on the experiment.

    A procedure is anything more complex than a single sequence.
    It can be a sequence with some analysis performed afterward, a sequence that is run
    multiple times with different parameters, multiple sequences that must be run
    cohesively, etc...

    Procedures are created with :meth:`ExperimentManager.create_procedure`.

    The procedure must be active to start running sequences.
    A procedure is activated by using it as a context manager.
    No two procedures can be active at the same time.
    If a previous procedure is active, entering another procedure will block until the
    first procedure is exited.

    To run a sequence once a procedure is active, use :meth:`run_sequence`.

    Examples:

    .. code-block:: python

            experiment_manager: ExperimentManager = ...
            with experiment_manager.create_procedure("my procedure") as procedure:
                procedure.run_sequence(PureSequencePath("my sequence"))
                # do analysis, overwrite parameters, etc...
                procedure.run_sequence(PureSequencePath("another sequence"))
    """

    @abc.abstractmethod
    def is_active(self) -> bool:
        """Indicates if the procedure is currently active and can run sequences."""

        raise NotImplementedError

    @abc.abstractmethod
    def is_running_sequence(self) -> bool:
        """Indicates if the procedure is currently running a sequence."""

        raise NotImplementedError

    @abc.abstractmethod
    def exception(self) -> Optional[Exception]:
        """Retrieve the exception that occurred while running the last sequence.

        If a sequence is currently running, this method will block until the sequence
        is finished.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def start_sequence(
        self,
        sequence_path: PureSequencePath,
        device_configurations: Optional[Set[uuid.UUID]] = None,
        constant_tables: Optional[Set[uuid.UUID]] = None,
    ) -> None:
        """Start running the sequence on the setup.

        This method returns immediately, and the sequence is launched in a separate
        thread.

        Exceptions that occur while running the sequence are not raised by this method,
        but can be retrieved with the `exception` method.

        Args:
            sequence_path: the path of the sequence to run.
            device_configurations: the uuids of the device configurations to use for
            running this sequence.
            If None, this will default to the device configurations that are currently
            in use.
            constant_tables: the uuids of the constant tables to use for running this
            sequence.
            If None, this will default to the constant tables that are currently in use.
        Raises:
            ProcedureNotActiveError: if the procedure is not active.
            SequenceAlreadyRunningError: if a sequence is already running.
        """

        raise NotImplementedError

    def run_sequence(
        self,
        sequence_path: PureSequencePath,
        device_configurations: Optional[Set[uuid.UUID]] = None,
        constant_tables: Optional[Set[uuid.UUID]] = None,
    ) -> None:
        """Run a sequence on the setup.

        This method blocks until the sequence is finished.

        Arguments are the same as :meth:`start_sequence`.

        Raises:
            ProcedureNotActiveError: if the procedure is not active.
            SequenceAlreadyRunningError: if a sequence is already running.
            Exception: if an exception occurs while running the sequence.
        """

        self.start_sequence(sequence_path, device_configurations, constant_tables)
        if exception := self.exception():
            raise exception

    @abc.abstractmethod
    def sequences(self) -> list[PureSequencePath]:
        """Retrieve the list of sequences that were started by the procedure.

        Returns:
            A list of sequences that were started by the procedure since it was started,
            ordered by execution order.
            If the procedure is currently running a sequence, the sequence will be the
            last element of the list.
        """

        raise NotImplementedError


class BoundExperimentManager(ExperimentManager):
    def __init__(self, session_maker: ExperimentSessionMaker):
        self._procedure_running = threading.Lock()
        self._session_maker = session_maker
        self._thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    def __enter__(self):
        self._thread_pool.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        with self._procedure_running:
            return self._thread_pool.__exit__(exc_type, exc_value, traceback)

    def create_procedure(self, procedure_name: str) -> BoundProcedure:
        return BoundProcedure(
            procedure_name,
            self._session_maker,
            self._procedure_running,
            self._thread_pool,
        )


class BoundProcedure(Procedure):
    """Implementation of :class:`Procedure`.

    See :class:`Procedure` for documentation.

    This class is not meant to be instantiated directly, but is returned by
    :meth:`BoundExperimentManager.create_procedure`.
    """

    def __init__(
        self,
        name: str,
        session_maker: ExperimentSessionMaker,
        lock: threading.Lock,
        thread_pool: concurrent.futures.ThreadPoolExecutor,
    ):
        self._name = name
        self._session_maker = session_maker
        self._running = lock
        self._thread_pool = thread_pool
        self._sequence_future: Optional[concurrent.futures.Future] = None
        self._sequences: list[PureSequencePath] = []

    def __enter__(self):
        self._running.acquire()
        self._sequences.clear()
        return self

    def is_active(self) -> bool:
        return self._running.locked()

    def is_running_sequence(self) -> bool:
        return self._sequence_future is not None and not self._sequence_future.done()

    def sequences(self) -> list[PureSequencePath]:
        return self._sequences.copy()

    def exception(self) -> Optional[Exception]:
        if self._sequence_future is None:
            return None
        return self._sequence_future.exception()

    def start_sequence(
        self,
        sequence_path: PureSequencePath,
        device_configurations: Optional[Set[uuid.UUID]] = None,
        constant_tables: Optional[Set[uuid.UUID]] = None,
    ) -> None:
        if not self.is_active():
            raise ProcedureNotActiveError("The procedure is not active.")
        if self.is_running_sequence():
            raise SequenceAlreadyRunningError("A sequence is already running.")
        self._sequence_future = self._thread_pool.submit(
            self._run_sequence, sequence_path
        )
        self._sequences.append(sequence_path)

    def _run_sequence(self, sequence_path: PureSequencePath) -> None:
        time.sleep(5)
        raise NotImplementedError

    def __exit__(self, exc_type, exc_value, traceback):
        self._running.release()


class SequenceAlreadyRunningError(RuntimeError):
    pass


class ProcedureNotActiveError(RuntimeError):
    pass
