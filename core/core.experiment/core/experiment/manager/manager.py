from __future__ import annotations

import abc
import threading
from contextlib import AbstractContextManager

from core.session import ExperimentSessionMaker, PureSequencePath


class ExperimentManager(abc.ABC):
    @abc.abstractmethod
    def create_procedure(self, procedure_name: str) -> BaseProcedure:
        raise NotImplementedError


class BaseProcedure(AbstractContextManager, abc.ABC):
    @abc.abstractmethod
    def run_sequence(self, sequence_path: PureSequencePath) -> None:
        raise NotImplementedError


class ConcreteExperimentManager(ExperimentManager):
    def __init__(self, session_maker: ExperimentSessionMaker):
        self._procedure_running = threading.Lock()
        self._session_maker = session_maker

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        with self._procedure_running:
            return

    def create_procedure(self, procedure_name: str) -> ConcreteProcedure:
        return ConcreteProcedure(
            procedure_name, self._session_maker, self._procedure_running
        )


class ConcreteProcedure(BaseProcedure):
    def __init__(
        self, name: str, session_maker: ExperimentSessionMaker, lock: threading.Lock
    ):
        self._name = name
        self._session_maker = session_maker
        self._running = lock

    def __enter__(self):
        self._running.acquire()
        return self

    def run_sequence(self, sequence_path: PureSequencePath) -> None:
        if not self._running.locked():
            raise ProcedureNotRunningError(f"Procedure {self._name} is not running")

    def __exit__(self, exc_type, exc_value, traceback):
        self._running.release()


class ProcedureNotRunningError(RuntimeError):
    pass
