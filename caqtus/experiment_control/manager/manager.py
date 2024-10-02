from __future__ import annotations

import abc
import concurrent.futures
import logging
import threading
from collections.abc import Mapping
from contextlib import AbstractContextManager
from typing import Optional, assert_type

import anyio
import anyio.from_thread

from caqtus.device import DeviceConfiguration, DeviceName
from caqtus.session import (
    ExperimentSessionMaker,
    PureSequencePath,
    ExperimentSession,
    State,
    PathNotFoundError,
    PathIsNotSequenceError,
    TracebackSummary,
)
from caqtus.types.parameter import ParameterNamespace
from ..device_manager_extension import DeviceManagerExtensionProtocol
from ..sequence_execution import ShotRetryConfig, run_sequence
from ...utils._result import is_failure_type, Success

logger = logging.getLogger(__name__)


class ExperimentManager(abc.ABC):
    @abc.abstractmethod
    def create_procedure(
        self, procedure_name: str, acquisition_timeout: Optional[float] = None
    ) -> Procedure:
        raise NotImplementedError

    @abc.abstractmethod
    def interrupt_running_procedure(self) -> bool:
        """Indicates to the active procedure that it must stop running sequences.

        Returns:
            True if there was an active procedure, and it signaled that it will stop
            running sequences.
            False if no procedure was active.
        """

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
    def exception(self) -> Optional[BaseException]:
        """Retrieve the exception that occurred while running the last sequence.

        If a sequence is currently running, this method will block until the sequence
        is finished.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def start_sequence(
        self,
        sequence: PureSequencePath,
        global_parameters: Optional[ParameterNamespace] = None,
        device_configurations: Optional[
            Mapping[DeviceName, DeviceConfiguration]
        ] = None,
    ) -> None:
        """Start running the sequence on the setup.

        This method returns immediately, and the sequence is launched in a separate
        thread.

        Exceptions that occur while running the sequence are not raised by this method,
        but can be retrieved with the `exception` method.

        Args:
            sequence: the sequence to run.
            global_parameters: The parameters to set for this sequence.
            If nothing is passed, it will take the current global parameters from the
            session.
            device_configurations: the device configurations to use for running this
            sequence.
            If None, this will use the session default device configurations.
        Raises:
            ProcedureNotActiveError: if the procedure is not active.
            SequenceAlreadyRunningError: if a sequence is already running.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def interrupt_sequence(self) -> bool:
        """Interrupt the currently running sequence.

        This method only signals the sequence that it must interrupt as soon as
        possible, but it does not wait for the sequence to finish.
        To wait for the sequence to finish, use :meth:`wait_until_sequence_finished`
        after calling :meth:`interrupt_sequence`.

        Returns:
            True if a sequence was running and was interrupted.
            False if no sequence was running.
        """

        raise NotImplementedError

    def run_sequence(
        self,
        sequence: PureSequencePath,
        global_parameters: Optional[ParameterNamespace] = None,
        device_configurations: Optional[
            Mapping[DeviceName, DeviceConfiguration]
        ] = None,
    ) -> None:
        """Run a sequence on the setup.

        This method blocks until the sequence is finished.

        Arguments are the same as :meth:`start_sequence`.

        Raises:
            ProcedureNotActiveError: if the procedure is not active.
            SequenceAlreadyRunningError: if a sequence is already running.
            Exception: if an exception occurs while running the sequence.
        """

        self.start_sequence(sequence, global_parameters, device_configurations)
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


class LocalExperimentManager(ExperimentManager):
    """Implementation of :class:`ExperimentManager` that runs in the local process."""

    def __init__(
        self,
        session_maker: ExperimentSessionMaker,
        device_manager_extension: DeviceManagerExtensionProtocol,
        shot_retry_config: Optional[ShotRetryConfig] = None,
    ):
        self._procedure_running = threading.Lock()
        self._session_maker = session_maker
        self._shot_retry_config = shot_retry_config or ShotRetryConfig()
        self._thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self._active_procedure: Optional[BoundProcedure] = None
        self._device_manager_extension = device_manager_extension

        # We crash the sequences that might have been running previously.
        # This ensures that only one experiment manager is active at a time.
        # It also cleans up previous sequences that might still be running if the
        # previous experiment manager was not properly closed.
        self._crash_running_sequences()

    def _crash_running_sequences(self) -> None:
        with self._session_maker() as session:
            _crash_running_sequences(session)

    def __enter__(self):
        self._thread_pool.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        with self._procedure_running:
            return self._thread_pool.__exit__(exc_type, exc_value, traceback)

    def create_procedure(
        self, procedure_name: str, acquisition_timeout: Optional[float] = None
    ) -> BoundProcedure:
        return BoundProcedure(
            experiment_manager=self,
            name=procedure_name,
            session_maker=self._session_maker,
            lock=self._procedure_running,
            thread_pool=self._thread_pool,
            shot_retry_config=self._shot_retry_config,
            acquisition_timeout=acquisition_timeout,
            device_manager_extension=self._device_manager_extension,
        )

    def interrupt_running_procedure(self) -> bool:
        if self._active_procedure is None:
            return False
        return self._active_procedure.interrupt_sequence()


class BoundProcedure(Procedure):
    """Implementation of :class:`Procedure`.

    See :class:`Procedure` for documentation.

    This class is not meant to be instantiated directly, but is returned by
    :meth:`BoundExperimentManager.create_procedure`.
    """

    def __init__(
        self,
        experiment_manager: LocalExperimentManager,
        name: str,
        session_maker: ExperimentSessionMaker,
        lock: threading.Lock,
        thread_pool: concurrent.futures.ThreadPoolExecutor,
        shot_retry_config: ShotRetryConfig,
        device_manager_extension: DeviceManagerExtensionProtocol,
        acquisition_timeout: Optional[float] = None,
    ):
        self._parent = experiment_manager
        self._name = name
        self._session_maker = session_maker
        self._running = lock
        self._thread_pool = thread_pool
        self._sequence_future: Optional[concurrent.futures.Future] = None
        self._sequences: list[PureSequencePath] = []
        self._acquisition_timeout = acquisition_timeout if acquisition_timeout else -1
        self._shot_retry_config = shot_retry_config
        self._device_manager_extension = device_manager_extension
        self._cancel_scope: Optional[anyio.CancelScope] = None
        self._portal: Optional[anyio.from_thread.BlockingPortal] = None

    def __repr__(self):
        return f"<{self.__class__.__name__}('{self}') at {hex(id(self))}>"

    def __str__(self):
        return self._name

    def __enter__(self):
        if not self._running.acquire(timeout=self._acquisition_timeout):
            raise TimeoutError(f"Could not activate procedure <{self}>.")
        self._parent._active_procedure = self
        self._sequences.clear()
        return self

    def is_active(self) -> bool:
        return self._running.locked()

    def is_running_sequence(self) -> bool:
        return self._sequence_future is not None and not self._sequence_future.done()

    def sequences(self) -> list[PureSequencePath]:
        return self._sequences.copy()

    def exception(self) -> Optional[BaseException]:
        if self._sequence_future is None:
            return None
        return self._sequence_future.exception()

    def start_sequence(
        self,
        sequence: PureSequencePath,
        global_parameters: Optional[ParameterNamespace] = None,
        device_configurations: Optional[
            Mapping[DeviceName, DeviceConfiguration]
        ] = None,
    ) -> None:
        if not self.is_active():
            exception = ProcedureNotActiveError("The procedure is not active.")
            exception.add_note(
                "It is only possible to run sequences inside active procedures."
            )
            exception.add_note(
                "Maybe you forgot to use the procedure inside a `with` statement?"
            )
            raise exception
        if self.is_running_sequence():
            raise SequenceAlreadyRunningError("A sequence is already running.")
        self._sequence_future = self._thread_pool.submit(
            self._run_sequence,
            sequence,
            global_parameters,
            device_configurations,
        )
        self._sequences.append(sequence)

    def interrupt_sequence(self) -> bool:
        if not self.is_running_sequence():
            return False
        assert self._cancel_scope is not None
        assert self._portal is not None
        self._portal.call(self._cancel_scope.cancel)
        return True

    def wait_until_sequence_finished(self):
        if self.is_running_sequence():
            assert self._sequence_future is not None
            self._sequence_future.result()

    def _run_sequence(
        self,
        sequence: PureSequencePath,
        global_parameters: Optional[ParameterNamespace] = None,
        device_configurations: Optional[
            Mapping[DeviceName, DeviceConfiguration]
        ] = None,
    ) -> None:
        async def run():
            with anyio.CancelScope() as self._cancel_scope:
                async with anyio.from_thread.BlockingPortal() as self._portal:
                    await run_sequence(
                        sequence=sequence,
                        session_maker=self._session_maker,
                        shot_retry_config=self._shot_retry_config,
                        global_parameters=global_parameters,
                        device_configurations=device_configurations,
                        device_manager_extension=self._device_manager_extension,
                    )

        try:
            anyio.run(run, backend="trio")
        except Exception as e:
            logger.error(f"Error while running sequence {sequence}.", exc_info=e)
        self._cancel_scope = None

    def __exit__(self, exc_type, exc_value, traceback):
        error_occurred = exc_value is not None
        try:
            if error_occurred:
                self.interrupt_sequence()
            self.wait_until_sequence_finished()
        finally:
            self._parent._active_procedure = None
            self._running.release()


def _crash_running_sequences(session: ExperimentSession) -> None:
    tb_summary = TracebackSummary.from_exception(
        RuntimeError(
            "Sequence was already running when the experiment manager started."
        )
    )
    for path in session.sequences.get_sequences_in_state(State.RUNNING):
        result = session.sequences.set_crashed(path, tb_summary)
        assert not is_failure_type(result, PathNotFoundError)
        assert not is_failure_type(result, PathIsNotSequenceError)
        assert_type(result, Success[None])
    for path in session.sequences.get_sequences_in_state(State.PREPARING):
        result = session.sequences.set_crashed(path, tb_summary)
        assert not is_failure_type(result, PathNotFoundError)
        assert not is_failure_type(result, PathIsNotSequenceError)
        assert_type(result, Success[None])


class SequenceAlreadyRunningError(RuntimeError):
    pass


class ProcedureNotActiveError(RuntimeError):
    pass
