from __future__ import annotations

import abc
import concurrent.futures
import logging
import threading
import uuid
from collections.abc import Set
from contextlib import AbstractContextManager
from typing import Optional

from core.compilation import ShotCompilerFactory
from core.device import DeviceConfigurationAttrs, DeviceName
from core.session import (
    ExperimentSessionMaker,
    PureSequencePath,
    ConstantTable,
    Sequence,
)
from core.session.sequence.iteration_configuration import StepsConfiguration

from ..sequence_runner import SequenceManager, StepSequenceRunner, ShotRetryConfig
from ..shot_runner import ShotRunnerFactory
from util import log_exception

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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
    def exception(self) -> Optional[Exception]:
        """Retrieve the exception that occurred while running the last sequence.

        If a sequence is currently running, this method will block until the sequence
        is finished.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def start_sequence(
        self,
        sequence: Sequence,
        device_configurations_uuids: Optional[Set[uuid.UUID]] = None,
        constant_tables_uuids: Optional[Set[uuid.UUID]] = None,
    ) -> None:
        """Start running the sequence on the setup.

        This method returns immediately, and the sequence is launched in a separate
        thread.

        Exceptions that occur while running the sequence are not raised by this method,
        but can be retrieved with the `exception` method.

        Args:
            sequence: the sequence to run.
            device_configurations_uuids: the uuids of the device configurations to use for
            running this sequence.
            If None, this will default to the device configurations that are currently
            in use.
            constant_tables_uuids: the uuids of the constant tables to use for running this
            sequence.
            If None, this will default to the constant tables that are currently in use.
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
        sequence: Sequence,
        device_configurations_uuids: Optional[Set[uuid.UUID]] = None,
        constant_tables_uuids: Optional[Set[uuid.UUID]] = None,
    ) -> None:
        """Run a sequence on the setup.

        This method blocks until the sequence is finished.

        Arguments are the same as :meth:`start_sequence`.

        Raises:
            ProcedureNotActiveError: if the procedure is not active.
            SequenceAlreadyRunningError: if a sequence is already running.
            Exception: if an exception occurs while running the sequence.
        """

        self.start_sequence(
            sequence, device_configurations_uuids, constant_tables_uuids
        )
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
    def __init__(
        self,
        session_maker: ExperimentSessionMaker,
        shot_compiler_factory: ShotCompilerFactory,
        shot_runner_factory: ShotRunnerFactory,
        shot_retry_config: Optional[ShotRetryConfig] = None,
    ):
        self._procedure_running = threading.Lock()
        self._session_maker = session_maker
        self._shot_compiler_factory = shot_compiler_factory
        self._shot_runner_factory = shot_runner_factory
        self._shot_retry_config = shot_retry_config
        self._thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self._active_procedure: Optional[BoundProcedure] = None

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
            self,
            procedure_name,
            self._session_maker,
            self._procedure_running,
            self._thread_pool,
            self._shot_compiler_factory,
            self._shot_runner_factory,
            self._shot_retry_config,
            acquisition_timeout,
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
        experiment_manager: BoundExperimentManager,
        name: str,
        session_maker: ExperimentSessionMaker,
        lock: threading.Lock,
        thread_pool: concurrent.futures.ThreadPoolExecutor,
        shot_compiler_factory: ShotCompilerFactory,
        shot_runner_factory: ShotRunnerFactory,
        shot_retry_config: ShotRetryConfig,
        acquisition_timeout: Optional[float] = None,
    ):
        self._parent = experiment_manager
        self._name = name
        self._session_maker = session_maker
        self._running = lock
        self._thread_pool = thread_pool
        self._sequence_future: Optional[concurrent.futures.Future] = None
        self._sequences: list[Sequence] = []
        self._acquisition_timeout = acquisition_timeout if acquisition_timeout else -1
        self._shot_compiler_factory = shot_compiler_factory
        self._shot_runner_factory = shot_runner_factory
        self._shot_retry_config = shot_retry_config
        self._must_interrupt = threading.Event()

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

    def sequences(self) -> list[Sequence]:
        return self._sequences.copy()

    def exception(self) -> Optional[Exception]:
        if self._sequence_future is None:
            return None
        return self._sequence_future.exception()

    def start_sequence(
        self,
        sequence: Sequence,
        device_configurations_uuids: Optional[Set[uuid.UUID]] = None,
        constant_tables_uuids: Optional[Set[uuid.UUID]] = None,
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
        self._must_interrupt.clear()
        self._sequence_future = self._thread_pool.submit(
            self._run_sequence,
            sequence,
            device_configurations_uuids,
            constant_tables_uuids,
        )
        self._sequences.append(sequence)

    def interrupt_sequence(self) -> bool:
        if not self.is_running_sequence():
            return False
        self._must_interrupt.set()
        return True

    def wait_until_sequence_finished(self):
        if self.is_running_sequence():
            self._sequence_future.result()

    @log_exception(logger)
    def _run_sequence(
        self,
        sequence: Sequence,
        device_configurations_uuids: Optional[Set[uuid.UUID]] = None,
        constant_tables_uuids: Optional[Set[uuid.UUID]] = None,
    ) -> None:
        with self._session_maker() as session:
            iteration = session.sequences.get_iteration_configuration(sequence.path)

        with SequenceManager(
            sequence,
            self._session_maker,
            self._shot_compiler_factory,
            self._shot_runner_factory,
            self._must_interrupt,
            self._shot_retry_config,
            device_configurations_uuids,
            constant_tables_uuids,
        ) as sequence_manager:
            if not isinstance(iteration, StepsConfiguration):
                raise NotImplementedError("Only steps iteration is supported.")
            sequence_runner = StepSequenceRunner(
                sequence_manager, sequence_manager.constant_tables
            )
            sequence_runner.execute_steps(iteration.steps)

    def _get_device_configurations_to_use(
        self, device_configurations_uuids: Optional[Set[uuid.UUID]] = None
    ) -> dict[DeviceName, DeviceConfigurationAttrs]:
        with self._session_maker() as session:
            if device_configurations_uuids is None:
                device_configurations_uuids = (
                    session.device_configurations.get_in_use_uuids()
                )
            device_configurations = {
                session.device_configurations.get_device_name(
                    uuid_
                ): session.device_configurations.get_configuration(uuid_)
                for uuid_ in device_configurations_uuids
            }
        return device_configurations

    def _get_constant_tables_to_use(
        self, constant_tables_uuids: Optional[Set[uuid.UUID]] = None
    ) -> dict[str, ConstantTable]:
        with self._session_maker() as session:
            if constant_tables_uuids is None:
                constant_tables_uuids = session.constants.get_default_uuids()
            constant_tables = {
                session.constants.get_table_name(uuid_): session.constants.get_table(
                    uuid_
                )
                for uuid_ in constant_tables_uuids
            }
        return constant_tables

    def __exit__(self, exc_type, exc_value, traceback):
        error_occurred = exc_value is not None
        try:
            if error_occurred:
                self.interrupt_sequence()
            self.wait_until_sequence_finished()
        finally:
            self._parent._active_procedure = None
            self._running.release()


class SequenceAlreadyRunningError(RuntimeError):
    pass


class ProcedureNotActiveError(RuntimeError):
    pass


class ErrorWhileRunningSequence(RuntimeError):
    pass
