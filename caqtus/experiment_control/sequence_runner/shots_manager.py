from __future__ import annotations

import contextlib
import datetime
from collections.abc import AsyncGenerator, AsyncIterable
from typing import Mapping, Any, Protocol

import anyio
import anyio.to_process
import attrs

from caqtus.device import DeviceName
from caqtus.shot_compilation import VariableNamespace
from caqtus.types.data import DataLabel, Data
from .._logger import logger


class ShotRunner(Protocol):
    async def run_shot(
        self, device_parameters: Mapping[DeviceName, Mapping[str, Any]], timeout: float
    ) -> Mapping[DataLabel, Data]: ...


class ShotCompiler(Protocol):
    def compile_shot(
        self, shot_parameters: VariableNamespace
    ) -> tuple[Mapping[DeviceName, Mapping[str, Any]], float]: ...


class ShotManager:
    def __init__(
        self,
        shot_runner: ShotRunner,
        shot_compiler: ShotCompiler,
        shot_retry_config: ShotRetryConfig,
    ):
        self._shot_runner = shot_runner
        self._shot_compiler = shot_compiler
        self._shot_retry_config = shot_retry_config
        (
            self._shot_parameter_scheduler,
            self._shot_parameter_receiver,
        ) = anyio.create_memory_object_stream[ShotParameters]()
        (
            self._device_parameter_sender,
            self._device_parameter_receiver,
        ) = anyio.create_memory_object_stream[DeviceParameters](4)
        (
            self._shot_data_sender,
            self._shot_data_receiver,
        ) = anyio.create_memory_object_stream(4)
        self._current_shot = 0

    @contextlib.asynccontextmanager
    async def run(self) -> AsyncGenerator[AsyncIterable[ShotData], None]:
        try:
            async with anyio.create_task_group() as tg:
                async with self._device_parameter_sender, self._shot_parameter_receiver:
                    for _ in range(4):
                        tg.start_soon(
                            self._compile_shots,
                            self._shot_compiler,
                            self._shot_parameter_receiver.clone(),
                            self._device_parameter_sender.clone(),
                        )
                tg.start_soon(self._run_shots, self._shot_runner)
                async with self._shot_data_receiver:
                    yield self._shot_data_receiver
        except* anyio.BrokenResourceError:
            # We ignore this error because the error that caused it will anyway be
            # raised, and we don't want to clutter the exception traceback.
            # Can't use contextlib.suppress because it only supports exception groups
            # starting from Python 3.12.
            pass

    @contextlib.asynccontextmanager
    async def start_scheduling(self) -> AsyncGenerator[None, None]:
        async with self._shot_parameter_scheduler:
            yield

    async def schedule_shot(self, shot_variables: VariableNamespace) -> None:
        shot_parameters = ShotParameters(
            index=self._current_shot, parameters=shot_variables
        )
        try:
            await self._shot_parameter_scheduler.send(shot_parameters)
        except anyio.BrokenResourceError:
            # We ignore this error because the error that caused it will anyway be
            # raised, and we don't want to clutter the exception traceback.
            pass
        self._current_shot += 1

    @staticmethod
    async def _compile_shots(
        shot_compiler: ShotCompiler, shot_params_receiver, device_params_sender
    ):
        async with device_params_sender, shot_params_receiver:
            async for shot_parameters in shot_params_receiver:
                result = await anyio.to_process.run_sync(
                    _compile_shot, shot_parameters, shot_compiler
                )
                await device_params_sender.send(result)

    async def _run_shots(self, shot_runner: ShotRunner):
        async with (
            self._shot_data_sender,
            self._device_parameter_receiver as receiver,
        ):
            async for device_parameters in receiver:
                shot_data = await self._run_shot_with_retry(
                    device_parameters, shot_runner
                )
                await self._shot_data_sender.send(shot_data)

    async def _run_shot_with_retry(
        self, device_parameters: DeviceParameters, shot_runner: ShotRunner
    ) -> ShotData:
        exceptions_to_retry = self._shot_retry_config.exceptions_to_retry
        number_of_attempts = self._shot_retry_config.number_of_attempts
        if number_of_attempts < 1:
            raise ValueError("number_of_attempts must be >= 1")

        errors: list[Exception] = []

        for attempt in range(number_of_attempts):
            try:
                start_time = datetime.datetime.now(tz=datetime.timezone.utc)
                data = await shot_runner.run_shot(
                    device_parameters.device_parameters, device_parameters.timeout
                )
                end_time = datetime.datetime.now(tz=datetime.timezone.utc)
            except* exceptions_to_retry as e:
                errors.extend(e.exceptions)
                # We sleep a bit to allow to recover from the error, for example if it
                # is a timeout.
                await anyio.sleep(0.1)
                logger.warning(
                    f"Attempt {attempt+1}/{number_of_attempts} failed", exc_info=e
                )
            else:
                return ShotData(
                    index=device_parameters.index,
                    start_time=start_time,
                    end_time=end_time,
                    variables=device_parameters.shot_parameters,
                    data=data,
                )
        raise ExceptionGroup(
            f"Could not execute shot after {number_of_attempts} attempts", errors
        )


@attrs.frozen(order=True)
class ShotParameters:
    """Holds information necessary to compile a shot."""

    index: int
    parameters: VariableNamespace = attrs.field(eq=False)


@attrs.frozen(order=True)
class DeviceParameters:
    """Holds information necessary to run a shot."""

    index: int
    shot_parameters: VariableNamespace = attrs.field(eq=False)
    device_parameters: Mapping[DeviceName, Mapping[str, Any]] = attrs.field(eq=False)
    timeout: float = attrs.field()


@attrs.frozen(order=True)
class ShotData:
    """Holds information necessary to store a shot."""

    index: int
    start_time: datetime.datetime = attrs.field(eq=False)
    end_time: datetime.datetime = attrs.field(eq=False)
    variables: VariableNamespace = attrs.field(eq=False)
    data: Mapping[DataLabel, Data] = attrs.field(eq=False)


def _compile_shot(
    shot_parameters: ShotParameters, shot_compiler: ShotCompiler
) -> DeviceParameters:
    compiled, shot_duration = shot_compiler.compile_shot(shot_parameters.parameters)
    return DeviceParameters(
        index=shot_parameters.index,
        shot_parameters=shot_parameters.parameters,
        device_parameters=compiled,
        timeout=shot_duration + 10,
    )


@attrs.define
class ShotRetryConfig:
    """Specifies how to retry a shot if an error occurs.

    Attributes:
        exceptions_to_retry: If an exception occurs while running a shot, it will be
        retried if it is an instance of one of the exceptions in this tuple.
        number_of_attempts: The number of times to retry a shot if an error occurs.
    """

    exceptions_to_retry: tuple[type[Exception], ...] = attrs.field(
        factory=tuple,
        eq=False,
        on_setattr=attrs.setters.validate,
    )
    number_of_attempts: int = attrs.field(default=1, eq=False)
