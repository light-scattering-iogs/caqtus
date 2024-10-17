from __future__ import annotations

import contextlib
import datetime
import functools
import logging
import warnings
import weakref
from collections.abc import AsyncIterable, Awaitable, Callable
from typing import TypeVar

import anyio
import attrs
import tblib.pickling_support
from anyio.abc import TaskStatus
from anyio.streams.memory import MemoryObjectSendStream, MemoryObjectReceiveStream

from caqtus.device._controller import DeviceError
from caqtus.experiment_control.sequence_execution._async_utils import (
    task_group_with_error_message,
)
from caqtus.formatter import fmt
from caqtus.types._parameter_namespace import VariableNamespace
from caqtus.types.recoverable_exceptions import ShotAttemptsExceededError
from caqtus.utils.logging import log_async_cm_decorator, log_async_cm
from ._shot_compiler import ShotCompilerProtocol
from ._shot_primitives import DeviceParameters, ShotData, ShotParameters
from ._shot_runner import ShotRunnerProtocol

logger = logging.getLogger(__name__)

_log_async_cm = functools.partial(log_async_cm, logger=logger)


class ShotExecutionSorter:
    """Wraps a memory object send stream to ensure that shots are executed in order."""

    def __init__(self, shot_execution_stream: MemoryObjectSendStream[DeviceParameters]):
        self._shot_execution_stream = shot_execution_stream
        self._next_shot = 0
        self._can_push_events = weakref.WeakValueDictionary[int, anyio.Event]()

    async def push(self, shot_parameters: DeviceParameters) -> None:
        """Pushes a shot to the execution queue.

        Push the shot parameters to the execution queue when the shot index matches the
        next shot to run.
        """

        shot_index = shot_parameters.index
        if shot_index != self._next_shot:
            assert shot_index > self._next_shot
            try:
                event = self._can_push_events[shot_index]
            except KeyError:
                event = anyio.Event()
                self._can_push_events[shot_index] = event
            await event.wait()

        assert shot_index == self._next_shot

        await self._shot_execution_stream.send(shot_parameters)
        self._next_shot += 1
        try:
            self._can_push_events[self._next_shot].set()
        except KeyError:
            pass


class ShotManager:
    """Manages the execution of shots.

    This object acts as an execution queue for shots on the experiment.

    When a shot is scheduled, the shot parameters are compiled into device parameters.
    The device parameters are then queued to run a shot on the experiment.
    The data produced by the shot is then yielded. The data must be consumed to allow
    further shots to be executed and scheduled.

    Args:
        shot_runner: The object that will actually execute the shots on the experiment.
        shot_compiler: The object that compiles shot parameters into device parameters.
        shot_retry_config: Specifies how to retry a shot if an error occurs.
    """

    def __init__(
        self,
        shot_runner: ShotRunnerProtocol,
        shot_compiler: ShotCompilerProtocol,
        shot_retry_config: ShotRetryConfig,
    ):
        self._shot_runner = shot_runner
        self._shot_compiler = shot_compiler
        self._shot_retry_config = shot_retry_config

        self._exit_stack = contextlib.AsyncExitStack()

    async def __aenter__(
        self,
    ) -> tuple[
        contextlib.AbstractAsyncContextManager[ShotScheduler],
        contextlib.AbstractAsyncContextManager[AsyncIterable[ShotData]],
    ]:
        """Start background tasks to compile and run shots.

        Returns:
            A tuple with two objects:
            - A context manager that allows to schedule shots.
            - A context manager that yields shot data.

            The context managers must be entered and closed before the ShotManager is
            closed because it is necessary to know when all shots have been scheduled
            and the data has been consumed.

            The data produced must be consumed to allow further shots to be executed.
        """

        await self._exit_stack.__aenter__()
        (
            shot_data_send_stream,
            shot_data_receive_stream,
        ) = anyio.create_memory_object_stream[ShotData](1)
        task_group = await self._exit_stack.enter_async_context(
            task_group_with_error_message(
                "Errors occurred while managing shots execution"
            )
        )
        (
            device_parameters_send_stream,
            device_parameters_receive_stream,
        ) = anyio.create_memory_object_stream[DeviceParameters]()
        await task_group.start(
            self.run_shots,
            self._shot_runner,
            device_parameters_receive_stream,
            shot_data_send_stream,
        )
        (
            self._shot_parameters_send_stream,
            shot_parameters_receive_stream,
        ) = anyio.create_memory_object_stream[ShotParameters]()
        await task_group.start(
            self.compile_shots,
            self._shot_compiler,
            shot_parameters_receive_stream,
            device_parameters_send_stream,
        )

        return self.scheduler(), shot_data_receive_stream

    async def __aexit__(self, exc_type, exc_value, traceback):
        return await self._exit_stack.__aexit__(exc_type, exc_value, traceback)

    async def run_shots(
        self,
        shot_runner: ShotRunnerProtocol,
        device_parameters_output_stream: MemoryObjectReceiveStream[DeviceParameters],
        shot_data_input_stream: MemoryObjectSendStream[ShotData],
        *,
        task_status: TaskStatus[None] = anyio.TASK_STATUS_IGNORED,
    ) -> None:
        # Suppress BrokenResourceError because the stream if the stream is closed due
        # to an error on the other side, we don't want to clutter the traceback.
        with contextlib.suppress(anyio.BrokenResourceError):
            async with shot_data_input_stream, device_parameters_output_stream:
                task_status.started()
                async for device_parameters in device_parameters_output_stream:
                    try:
                        shot_data = await self._run_shot_with_retry(
                            device_parameters, shot_runner
                        )
                    except Exception as e:
                        raise RuntimeError(
                            fmt(
                                "An error occurred while executing {:shot}",
                                device_parameters.index,
                            )
                        ) from e
                    await send_fast(
                        shot_data_input_stream, shot_data, "generated shot data stream"
                    )

    @log_async_cm_decorator(logger)
    @contextlib.asynccontextmanager
    async def scheduler(self):
        """Returns an object that allows to schedule shots.

        Warnings:
            It does NOT support being called several times.
        """

        async with _log_async_cm(
            self._shot_parameters_send_stream, name="shot_parameters_input_stream"
        ):
            yield ShotScheduler(self._shot_parameters_send_stream)

    async def compile_shots(
        self,
        shot_compiler: ShotCompilerProtocol,
        shot_params_receive_stream: MemoryObjectReceiveStream[ShotParameters],
        device_parameters_send_stream: MemoryObjectSendStream[DeviceParameters],
        *,
        task_status: TaskStatus[None] = anyio.TASK_STATUS_IGNORED,
    ):
        async with (
            device_parameters_send_stream,
            task_group_with_error_message(
                "Errors occurred during shot compilation"
            ) as tg,
        ):
            shot_execution_queue = ShotExecutionSorter(device_parameters_send_stream)
            async with shot_params_receive_stream:
                for _ in range(4):
                    await tg.start(
                        self._compile_shots,
                        shot_compiler,
                        shot_params_receive_stream.clone(),
                        shot_execution_queue,
                    )
            task_status.started()

    async def _compile_shots(
        self,
        shot_compiler: ShotCompilerProtocol,
        shot_params_receive_stream: MemoryObjectReceiveStream[ShotParameters],
        shot_execution_queue: ShotExecutionSorter,
        *,
        task_status: TaskStatus[None] = anyio.TASK_STATUS_IGNORED,
    ) -> None:
        # Suppress BrokenResourceError because the stream if the stream is closed due
        # to an error on the other side, we don't want to clutter the traceback.
        with contextlib.suppress(anyio.BrokenResourceError):
            async with shot_params_receive_stream:
                task_status.started()
                async for shot_params in shot_params_receive_stream:
                    result = await self._compile_shot(shot_params, shot_compiler)
                    logger.debug(
                        "Pushing shot %d to execution queue.", shot_params.index
                    )
                    await shot_execution_queue.push(result)

    async def _run_shot_with_retry(
        self, device_parameters: DeviceParameters, shot_runner: ShotRunnerProtocol
    ) -> ShotData:
        data = await _run_shot_with_retry(
            functools.partial(run_shot, device_parameters, shot_runner),
            retry_condition(self._shot_retry_config.exceptions_to_retry),
            self._shot_retry_config.number_of_attempts,
        )
        return data

    async def _compile_shot(
        self, shot_parameters: ShotParameters, shot_compiler: ShotCompilerProtocol
    ) -> DeviceParameters:
        try:
            compiled, shot_duration = await shot_compiler.compile_shot(shot_parameters)
            result = DeviceParameters(
                index=shot_parameters.index,
                shot_parameters=shot_parameters.parameters,
                device_parameters=compiled,
                timeout=2 * shot_duration + 2,
            )
        except Exception as e:
            raise ShotCompilationError(
                fmt("An error occurred while compiling {:shot}", shot_parameters.index)
            ) from e
        return result


async def run_shot(
    device_parameters: DeviceParameters,
    shot_runner: ShotRunnerProtocol,
) -> ShotData:
    start_time = datetime.datetime.now(tz=datetime.timezone.utc)
    data = await shot_runner.run_shot(device_parameters)
    end_time = datetime.datetime.now(tz=datetime.timezone.utc)
    data = ShotData(
        index=device_parameters.index,
        start_time=start_time,
        end_time=end_time,
        variables=device_parameters.shot_parameters,
        data=data,
    )
    return data


async def _run_shot_with_retry(
    run: Callable[[], Awaitable[ShotData]],
    condition: Callable[[Exception], bool],
    number_of_attempts: int,
) -> ShotData:
    """Run a shot with retry logic.

    Args:
        run: A function to call to run the shot.
        condition: A function that determines if an exception is retriable.

            If the run function raises an exception group, the condition function will
            be tested against the exceptions in the group. If the condition function
            returns True for all the sub-exceptions, the shot will be retried.

        number_of_attempts: The maximum number of times to retry the shot if an error
            occurs.

            Must be >= 1.

    Returns:
        The data produced by the shot.

    Raises:
        ShotAttemptsExceededError: If the shot could not be executed after the number of
            attempts specified.
    """

    if number_of_attempts < 1:
        raise ValueError("number_of_attempts must be >= 1")

    errors: list[ExceptionGroup] = []

    for attempt in range(number_of_attempts):
        try:
            return await run()
        except BaseExceptionGroup as exc_group:
            retriable, others = exc_group.split(
                condition  # pyright: ignore[reportArgumentType, reportCallIssue]
            )
            if others:
                raise
            errors.append(
                ExceptionGroup(
                    f"Attempt {attempt+1}/{number_of_attempts} failed",
                    retriable.exceptions,
                )
            )
            logger.warning(
                f"Attempt {attempt+1}/{number_of_attempts} failed", exc_info=exc_group
            )
    raise ShotAttemptsExceededError(
        f"Could not execute shot after {number_of_attempts} attempts", errors
    )


def retry_condition(
    retriable_exceptions: tuple[type[Exception], ...]
) -> Callable[[Exception], bool]:
    def _retry_condition(e: Exception) -> bool:
        return isinstance(e, DeviceError) and isinstance(
            e.__cause__, retriable_exceptions
        )

    return _retry_condition


class ShotCompilationError(RuntimeError):
    """Error raised when an error occurs while compiling a shot."""

    pass


tblib.pickling_support.install(ShotCompilationError)


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


class ShotScheduler:
    def __init__(
        self,
        shot_parameters_input_stream: MemoryObjectSendStream[ShotParameters],
    ):
        self._shot_parameters_input_stream = shot_parameters_input_stream
        self._current_shot = 0

    async def schedule_shot(self, shot_variables: VariableNamespace) -> None:
        shot_parameters = ShotParameters(
            index=self._current_shot, parameters=shot_variables
        )
        with contextlib.suppress(anyio.BrokenResourceError):
            await self._shot_parameters_input_stream.send(shot_parameters)
        self._current_shot += 1


_T = TypeVar("_T")


async def send_fast(
    stream: MemoryObjectSendStream[_T], value: _T, stream_name: str
) -> None:
    try:
        return stream.send_nowait(value)
    except anyio.WouldBlock:
        try:
            with anyio.fail_after(1):
                await stream.send(value)
        except TimeoutError:
            raise RuntimeError(f"Could not push value to {stream_name}") from None
        message = (
            "The experiment produces data faster than it is consumed."
            "This might cause a slowdown of the experiment."
        )
        warnings.warn(message, stacklevel=2)
        logger.warning(message)
