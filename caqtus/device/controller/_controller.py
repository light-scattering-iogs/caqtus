from __future__ import annotations

import abc
import contextlib
import functools
from collections.abc import Callable, AsyncGenerator, Iterable, AsyncIterator
from typing import Generic, TypeVar, ParamSpec

import anyio
import anyio.to_thread

from caqtus.shot_event_dispatcher import ShotEventDispatcher
from caqtus.types.data import DataLabel, Data
from ..name import DeviceName
from ..runtime import Device

DeviceType = TypeVar("DeviceType", bound=Device)

ShotParametersType = TypeVar("ShotParametersType")

_T = TypeVar("_T")
_P = ParamSpec("_P")


class DeviceController(Generic[DeviceType, _P], abc.ABC):
    """Controls a device during a shot."""

    def __init__(
        self,
        device_name: DeviceName,
        shot_event_dispatcher: ShotEventDispatcher,
    ):
        self.device_name = device_name
        self.event_dispatcher = shot_event_dispatcher

    async def run_shot(
        self, device: DeviceType, /, *args: _P.args, **kwargs: _P.kwargs
    ) -> None:
        """Runs a shot on the device.

        This method must call :meth:`signal_ready` exactly once.
        The default method simply call :meth:`Device.update_parameters` with the
        arguments passed before the shot is launched.
        """

        await run_in_thread(device.update_parameters, *args, **kwargs)
        self.signal_ready()

    def signal_ready(self) -> None:
        """Indicates that the device has been programed and is ready to run the shot."""

        self.event_dispatcher.signal_device_ready(self.device_name)

    async def wait_all_devices_ready(self) -> None:
        """Waits for all devices to be ready to run the shot."""

        await self.event_dispatcher.wait_all_devices_ready()

    def signal_data_acquired(self, label: DataLabel, data: Data) -> None:
        """Signals that data has been acquired from the device."""

        self.event_dispatcher.signal_data_acquired(label, data)

    async def wait_data_acquired(self, label: DataLabel) -> Data:
        """Waits until the data with the given label has been acquired."""

        return await self.event_dispatcher.wait_data_acquired(label)

    def spawn_controller(
        self, controller_type: type[DeviceControllerType]
    ) -> DeviceControllerType:
        return controller_type(self.device_name, self.event_dispatcher)


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
