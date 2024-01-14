from __future__ import annotations

import concurrent.futures
import contextlib
import queue
import threading
import uuid
from collections.abc import Set, Mapping
from contextlib import AbstractContextManager
from typing import Optional, Any

import attrs

from core.compilation import ShotCompilerFactory, VariableNamespace
from core.device import DeviceName, DeviceParameter
from core.session import PureSequencePath, ExperimentSessionMaker
from core.session.sequence import State
from util.concurrent import TaskGroup


def nothing():
    pass


class SequenceManager(AbstractContextManager):
    def __init__(
        self,
        sequence_path: PureSequencePath,
        session_maker: ExperimentSessionMaker,
        shot_compiler_factory: ShotCompilerFactory,
        device_configurations_uuid: Optional[Set[uuid.UUID]] = None,
        constant_tables_uuid: Optional[Set[uuid.UUID]] = None,
    ) -> None:
        self._session_maker = session_maker
        self._sequence_path = sequence_path

        with self._session_maker() as session:
            if device_configurations_uuid is None:
                device_configurations_uuid = (
                    session.device_configurations.get_in_use_uuids()
                )
            self._device_configurations_uuid = device_configurations_uuid
            self.device_configurations = {
                session.device_configurations.get_device_name(
                    uuid_
                ): session.device_configurations.get_configuration(uuid_)
                for uuid_ in self._device_configurations_uuid
            }
            if constant_tables_uuid is None:
                constant_tables_uuid = session.constants.get_in_use_uuids()
            self._constant_tables_uuid = constant_tables_uuid
            self.constant_tables = {
                session.constants.get_table_name(uuid_): session.constants.get_table(
                    uuid_
                )
                for uuid_ in self._constant_tables_uuid
            }
            self.time_lanes = session.sequence_collection.get_time_lanes(
                self._sequence_path
            )
        self._shot_compiler = shot_compiler_factory(
            self.time_lanes, self.device_configurations
        )

        self._current_shot = 0
        self._is_shutting_down = threading.Event()
        self._exit_stack = contextlib.ExitStack()
        self._thread_pool = concurrent.futures.ThreadPoolExecutor()
        self._shot_parameter_queue = queue.PriorityQueue[ShotParameters](4)
        self._device_parameter_queue = queue.PriorityQueue[DeviceParameters](4)
        self._task_group = TaskGroup(self._thread_pool, name="SequenceManager")

    def __enter__(self):
        self._prepare_sequence()
        self._exit_stack.__enter__()
        try:
            self._exit_stack.enter_context(self._thread_pool)
            self._task_group.__enter__()
            self._task_group.create_task(self._compile_shots)
            self._task_group.create_task(self._run_shots)
            self._prepare()
            self._set_sequence_state(State.RUNNING)
        except Exception as e:
            self._exit_stack.__exit__(type(e), e, e.__traceback__)
            self._set_sequence_state(State.CRASHED)
            raise
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        error_occurred = exc_val is not None

        if error_occurred:
            self._is_shutting_down.set()

        if not self._is_shutting_down.is_set():
            self._shot_parameter_queue.join()
            self._device_parameter_queue.join()
            self._is_shutting_down.set()
        try:
            self._task_group.__exit__(exc_type, exc_val, exc_tb)
        except* SequenceInterruptedException:
            self._set_sequence_state(State.INTERRUPTED)
            raise
        except* Exception:
            self._set_sequence_state(State.CRASHED)
            raise
        else:
            if error_occurred:
                self._set_sequence_state(State.CRASHED)
            else:
                self._set_sequence_state(State.FINISHED)
        finally:
            self._exit_stack.__exit__(exc_type, exc_val, exc_tb)

    def schedule_shot(self, shot_parameters: VariableNamespace) -> None:
        shot_parameters = ShotParameters(
            index=self._current_shot, parameters=shot_parameters
        )

        def push_shot() -> bool:
            if self.is_shutting_down():
                raise RuntimeError(
                    "Cannot schedule shot while sequence manager is shutting down."
                )
            try:
                self._shot_parameter_queue.put(shot_parameters, timeout=20e-3)
            except queue.Full:
                return False
            else:
                return True

        while not push_shot():
            continue
        self._current_shot += 1

    def is_shutting_down(self) -> bool:
        return self._is_shutting_down.is_set()

    def _prepare_sequence(self):
        with self._session_maker() as session:
            session.sequence_collection.set_state(self._sequence_path, State.PREPARING)
            session.sequence_collection.set_device_configuration_uuids(
                self._sequence_path, self._device_configurations_uuid
            )
            session.sequence_collection.set_constant_table_uuids(
                self._sequence_path, self._constant_tables_uuid
            )

    def _set_sequence_state(self, state: State):
        with self._session_maker() as session:
            session.sequence_collection.set_state(self._sequence_path, state)

    def _prepare(self):
        pass

    def _compile_shots(self):
        while not self.is_shutting_down():
            try:
                shot_parameters = self._shot_parameter_queue.get(timeout=20e-3)
            except queue.Empty:
                continue
            try:
                compiled = self._shot_compiler.compile_shot(shot_parameters.parameters)
                device_parameters = DeviceParameters(
                    index=shot_parameters.index,
                    shot_parameters=shot_parameters.parameters,
                    device_parameters=compiled,
                )
                while not self.is_shutting_down():
                    try:
                        self._device_parameter_queue.put(
                            device_parameters, timeout=20e-3
                        )
                        break
                    except queue.Full:
                        continue
                self._shot_parameter_queue.task_done()
            except Exception:
                self._is_shutting_down.set()
                raise

    def _run_shots(self):
        while not self.is_shutting_down():
            try:
                device_parameters = self._device_parameter_queue.get(timeout=20e-3)
            except queue.Empty:
                continue
            try:
                self._run_shot(device_parameters)
                self._device_parameter_queue.task_done()
            except Exception:
                self._is_shutting_down.set()
                raise

    def _run_shot(self, device_parameters: DeviceParameters):
        raise NotImplementedError


@attrs.frozen(order=True)
class ShotParameters:
    """Holds information necessary to compile a shot."""

    index: int
    parameters: VariableNamespace = attrs.field(eq=False)


@attrs.frozen(order=True)
class DeviceParameters:
    index: int
    shot_parameters: VariableNamespace = attrs.field(eq=False)
    device_parameters: Mapping[DeviceName, Mapping[DeviceParameter, Any]] = attrs.field(
        eq=False
    )


class SequenceInterruptedException(RuntimeError):
    pass
