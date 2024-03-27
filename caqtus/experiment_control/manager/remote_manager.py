from __future__ import annotations

import multiprocessing.managers
import time
from collections.abc import Mapping
from typing import Optional

from tblib import pickling_support

from caqtus.device import DeviceName, DeviceConfigurationAttrs
from caqtus.session import ExperimentSessionMaker, Sequence, ParameterNamespace
from caqtus.session import PureSequencePath
from caqtus.shot_compilation import ShotCompilerFactory
from .manager import ExperimentManager, Procedure, BoundExperimentManager
from ..sequence_runner import ShotRetryConfig
from ..shot_runner import ShotRunnerFactory

# This is necessary to be able to pass exception properly between the experiment server
# process and the clients.
# It allows sending the exception cause, context, notes, and traceback.
# It is not safe since it allows arbitrary code execution upon unpickling.
pickling_support.install()

experiment_manager: Optional[BoundExperimentManager] = None


class ExperimentManagerProxy(ExperimentManager, multiprocessing.managers.BaseProxy):
    _exposed_ = ("create_procedure", "interrupt_running_procedure")
    _method_to_typeid_ = {
        "create_procedure": "ProcedureProxy",
    }

    def create_procedure(
        self, procedure_name: str, acquisition_timeout: Optional[float] = None
    ) -> ProcedureProxy:
        return self._callmethod("create_procedure", (procedure_name,))  # type: ignore

    def interrupt_running_procedure(self) -> bool:
        return self._callmethod("interrupt_running_procedure", ())  # type: ignore

    def __repr__(self):
        return f"<ExperimentManagerProxy at {hex(id(self))}>"


class ProcedureProxy(Procedure, multiprocessing.managers.BaseProxy):
    """Proxy for a procedure running in a different process.

    This object behaves like a :class:`Procedure` object and should be used like it, but
    it forwards all method calls to an actual procedure object running in a different
    process.
    """

    _exposed_ = (
        "__enter__",
        "__exit__",
        "is_active",
        "is_running_sequence",
        "sequences",
        "exception",
        "start_sequence",
        "interrupt_sequence",
        "run_sequence",
        "__str__",
    )
    _method_to_typeid_ = {"__enter__": "ProcedureProxy"}

    def __enter__(self):
        return self._callmethod("__enter__", ())

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._callmethod("__exit__", (None, exc_val, None))

    def __repr__(self):
        return f"<{self.__class__.__name__}('{self}') at {hex(id(self))}>"

    def __str__(self):
        return self._callmethod("__str__", ())

    def is_active(self) -> bool:
        return self._callmethod("is_active", ())  # type: ignore

    def is_running_sequence(self) -> bool:
        return self._callmethod("is_running_sequence", ())  # type: ignore

    def sequences(self) -> list[PureSequencePath]:
        return self._callmethod("sequences", ())  # type: ignore

    def exception(self) -> Optional[Exception]:
        while self.is_running_sequence():
            time.sleep(10e-3)
        return self._callmethod("exception", ())  # type: ignore

    def start_sequence(
        self,
        sequence: Sequence,
        global_parameters: Optional[ParameterNamespace] = None,
        device_configurations: Optional[
            Mapping[DeviceName, DeviceConfigurationAttrs]
        ] = None,
    ) -> None:
        return self._callmethod(
            "start_sequence",
            (sequence, global_parameters, device_configurations),
        )

    def interrupt_sequence(self) -> bool:
        return self._callmethod("interrupt_sequence", ())  # type: ignore

    def run_sequence(
        self,
        sequence: Sequence,
        global_parameters: Optional[ParameterNamespace] = None,
        device_configurations: Optional[
            Mapping[DeviceName, DeviceConfigurationAttrs]
        ] = None,
    ) -> None:
        # Here we can't just call the remote method `run_sequence`.
        # This is because this method takes a long time to return, since it waits for
        # the sequence to finish.
        # This means that we can't even raise KeyboardInterrupt while waiting for the
        # method to return.
        self.start_sequence(sequence, global_parameters, device_configurations)
        while self.is_running_sequence():
            time.sleep(10e-3)
        if exception := self.exception():
            raise exception


class _MultiprocessingServerManager(multiprocessing.managers.BaseManager):
    pass


def _get_experiment_manager() -> BoundExperimentManager:
    if experiment_manager is None:
        raise RuntimeError("Experiment manager not initialized")
    return experiment_manager


def _enter_experiment_manager() -> None:
    experiment_manager.__enter__()


def _exit_experiment_manager(exc_value) -> None:
    experiment_manager.__exit__(type(exc_value), exc_value, exc_value.__traceback__)


def _create_experiment_manager(
    session_maker: ExperimentSessionMaker,
    shot_compiler_factory: ShotCompilerFactory,
    shot_runner_factory: ShotRunnerFactory,
    shot_retry_config: Optional[ShotRetryConfig] = None,
) -> None:
    global experiment_manager
    experiment_manager = BoundExperimentManager(
        session_maker, shot_compiler_factory, shot_runner_factory, shot_retry_config
    )


_MultiprocessingServerManager.register(
    "create_experiment_manager", _create_experiment_manager, ExperimentManagerProxy
)
_MultiprocessingServerManager.register(
    "get_experiment_manager", _get_experiment_manager, ExperimentManagerProxy
)
_MultiprocessingServerManager.register(
    "enter_experiment_manager", _enter_experiment_manager
)
_MultiprocessingServerManager.register(
    "exit_experiment_manager", _exit_experiment_manager
)
_MultiprocessingServerManager.register("ProcedureProxy", None, ProcedureProxy)


class RemoteExperimentManagerServer:
    session_maker: Optional[ExperimentSessionMaker] = None

    def __init__(
        self,
        address: tuple[str, int],
        authkey: bytes,
        session_maker: ExperimentSessionMaker,
        shot_compiler_factory: ShotCompilerFactory,
        shot_runner_factory: ShotRunnerFactory,
        shot_retry_config: Optional[ShotRetryConfig] = None,
    ):
        self._session_maker = session_maker
        self._multiprocessing_manager = _MultiprocessingServerManager(
            address=address, authkey=authkey
        )
        self._shot_compiler_factory = shot_compiler_factory
        self._shot_runner_factory = shot_runner_factory
        self._shot_retry_config = shot_retry_config
        self._shot_runner_factory = shot_runner_factory
        self._shot_retry_config = shot_retry_config

    def __enter__(self):
        self._multiprocessing_manager.start()
        self._multiprocessing_manager.create_experiment_manager(
            self._session_maker,
            self._shot_compiler_factory,
            self._shot_runner_factory,
            self._shot_retry_config,
        )
        self._multiprocessing_manager.enter_experiment_manager()
        return self

    @staticmethod
    def serve_forever():
        while True:
            time.sleep(100e-3)

    def __exit__(self, exc_type, exc_value, traceback):
        self._multiprocessing_manager.exit_experiment_manager(exc_value)
        return self._multiprocessing_manager.__exit__(exc_type, exc_value, traceback)


class _MultiprocessingClientManager(multiprocessing.managers.BaseManager):
    pass


_MultiprocessingClientManager.register(
    "get_experiment_manager", None, ExperimentManagerProxy
)

_MultiprocessingClientManager.register("ProcedureProxy", None, ProcedureProxy)


class RemoteExperimentManagerClient:
    def __init__(self, address: tuple[str, int], authkey: bytes):
        self._multiprocessing_manager = _MultiprocessingClientManager(
            address=address, authkey=authkey
        )
        self._multiprocessing_manager.connect()

    def get_experiment_manager(self) -> ExperimentManagerProxy:
        return self._multiprocessing_manager.get_experiment_manager()
