import abc
import contextlib
import functools
from collections.abc import Callable, AsyncGenerator, Iterable, AsyncIterator
from typing import Generic, TypeVar, ParamSpec

import anyio
import anyio.to_thread

from caqtus.shot_event_dispatcher import ShotEventDispatcher
from .. import DeviceName
from ..runtime import Device
from ...types.data import DataLabel, Data

DeviceType = TypeVar("DeviceType", bound=Device)

ShotParametersType = TypeVar("ShotParametersType")

_T = TypeVar("_T")
_P = ParamSpec("_P")


class DeviceController(Generic[DeviceType, ShotParametersType], abc.ABC):
    """Controls a device during a shot."""

    def __init__(
        self,
        device_name: DeviceName,
        shot_event_dispatcher: ShotEventDispatcher,
    ):
        #
        self.device_name = device_name
        self.event_dispatcher = shot_event_dispatcher

    @abc.abstractmethod
    async def run_shot(
        self, device: DeviceType, shot_parameters: ShotParametersType
    ) -> None:
        """Runs a shot on the device.

        This method must call :meth:`signal_ready` exactly once.
        """

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
