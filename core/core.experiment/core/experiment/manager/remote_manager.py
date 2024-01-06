from __future__ import annotations

import multiprocessing.managers
import time
from typing import Optional

from core.session import ExperimentSessionMaker
from core.session import PureSequencePath
from .manager import ExperimentManager, Procedure, BoundExperimentManager

experiment_manager: Optional[BoundExperimentManager] = None


class ExperimentManagerProxy(ExperimentManager, multiprocessing.managers.BaseProxy):
    _exposed_ = "create_procedure"
    _method_to_typeid_ = {
        "create_procedure": "ProcedureProxy",
    }

    def create_procedure(self, procedure_name: str) -> ProcedureProxy:
        return self._callmethod("create_procedure", (procedure_name,))  # type: ignore


class ProcedureProxy(Procedure, multiprocessing.managers.BaseProxy):
    _exposed_ = ("run_sequence", "__enter__", "__exit__")
    _method_to_typeid_ = {"__enter__": "ProcedureProxy"}

    def run_sequence(self, sequence_path: PureSequencePath) -> None:
        return self._callmethod("run_sequence", (sequence_path,))

    def __enter__(self):
        return self._callmethod("__enter__", ())

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._callmethod("__exit__", (exc_type, exc_val, exc_tb))


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
) -> None:
    global experiment_manager
    experiment_manager = BoundExperimentManager(session_maker)


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
    ):
        self._session_maker = session_maker
        self._multiprocessing_manager = _MultiprocessingServerManager(
            address=address, authkey=authkey
        )

    def __enter__(self):
        self._multiprocessing_manager.start()
        self._multiprocessing_manager.create_experiment_manager(self._session_maker)
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
