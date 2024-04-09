from __future__ import annotations

import abc
import contextlib
import functools
from collections.abc import Callable, AsyncGenerator, Iterable, AsyncIterator
from typing import (
    Generic,
    TypeVar,
    ParamSpec,
    TYPE_CHECKING,
    final,
    Optional,
    TypedDict,
)

import anyio
import anyio.to_thread

from caqtus.types.data import DataLabel, Data
from ..name import DeviceName
from ..runtime import Device

if TYPE_CHECKING:
    from caqtus.experiment_control._shot_handling import ShotEventDispatcher


DeviceType = TypeVar("DeviceType", bound=Device)

ShotParametersType = TypeVar("ShotParametersType")

_T = TypeVar("_T")
_P = ParamSpec("_P")


class DeviceController(Generic[DeviceType, _P], abc.ABC):
    """Controls a device during a shot."""

    def __init__(
        self,
        device_name: DeviceName,
        shot_event_dispatcher: "ShotEventDispatcher",
    ):
        self.device_name = device_name
        self._event_dispatcher = shot_event_dispatcher
        self._signaled_ready = anyio.Event()
        self._signaled_ready_time: Optional[float] = None
        self._finished_waiting_ready_time: Optional[float] = None

    async def run_shot(
        self, device: DeviceType, /, *args: _P.args, **kwargs: _P.kwargs
    ) -> None:
        """Runs a shot on the device.

        This method must call :meth:`wait_all_devices_ready` exactly once.
        The default method simply call :meth:`Device.update_parameters` with the
        arguments passed before the shot is launched.
        """

        await run_in_thread(device.update_parameters, *args, **kwargs)
        await self.wait_all_devices_ready()

    @final
    async def _run_shot(
        self, device: DeviceType, *args: _P.args, **kwargs: _P.kwargs
    ) -> ShotStats:
        await self.run_shot(device, *args, **kwargs)
        if not self._signaled_ready.is_set():
            raise RuntimeError(
                f"wait_all_devices_ready was not called in run_shot for {self}"
            )
        assert self._signaled_ready_time is not None
        assert self._finished_waiting_ready_time is not None

        return ShotStats(
            signaled_ready_time=self._signaled_ready_time,
            finished_waiting_ready_time=self._finished_waiting_ready_time,
        )

    @final
    async def wait_all_devices_ready(self) -> None:
        """Wait for all devices to be ready for time-sensitive operations.

        This method must be called once the device has been programmed for the shot and
        is ready to be triggered or to react to data acquisition signals.

        It must be called exactly once in :meth:`run_shot`.

        The method will wait for all devices to be ready before returning.
        """

        if self._signaled_ready.is_set():
            raise RuntimeError(
                f"wait_all_devices_ready must be called exactly once for {self}"
            )
        self._signaled_ready.set()
        self._signaled_ready_time = self._event_dispatcher.shot_time()
        await self._event_dispatcher.wait_all_devices_ready()
        self._finished_waiting_ready_time = self._event_dispatcher.shot_time()

    @final
    def signal_data_acquired(self, label: DataLabel, data: Data) -> None:
        """Signals that data has been acquired from the device."""

        self._event_dispatcher.signal_data_acquired(self.device_name, label, data)

    @final
    async def wait_data_acquired(self, label: DataLabel) -> Data:
        """Waits until the data with the given label has been acquired."""

        return await self._event_dispatcher.wait_data_acquired(self.device_name, label)

    def _debug_stats(self):
        return {
            "signaled_ready_time": self._signaled_ready_time,
            "finished_waiting_ready_time": self._finished_waiting_ready_time,
        }

    def spawn_controller(
        self, controller_type: type[DeviceControllerType]
    ) -> DeviceControllerType:
        return controller_type(self.device_name, self._event_dispatcher)


class ShotStats(TypedDict):
    signaled_ready_time: float
    finished_waiting_ready_time: float


DeviceControllerType = TypeVar("DeviceControllerType", bound=DeviceController)


async def run_in_thread(
    func: Callable[_P, _T], *args: _P.args, **kwargs: _P.kwargs
) -> _T:
    return await anyio.to_thread.run_sync(functools.partial(func, *args, **kwargs))


async def sleep(seconds: float) -> None:
    await anyio.sleep(seconds)


@contextlib.asynccontextmanager
async def async_context(
    cm: contextlib.AbstractContextManager[_T],
) -> AsyncGenerator[_T, None]:
    entered = await run_in_thread(cm.__enter__)
    try:
        yield entered
    except BaseException as exc:
        cm.__exit__(type(exc), exc, exc.__traceback__)
        raise
    else:
        await run_in_thread(cm.__exit__, None, None, None)


async def iterate_async(iterable: Iterable[_T]) -> AsyncIterator[_T]:
    iterator = iter(iterable)
    done = object()
    while (value := await run_in_thread(next, iterator, done)) is not done:
        yield value
