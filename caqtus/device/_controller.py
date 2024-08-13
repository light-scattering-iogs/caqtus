from __future__ import annotations

import abc
import functools
import logging
from collections.abc import Callable
from typing import (
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
from ._name import DeviceName
from .remote import DeviceProxy

if TYPE_CHECKING:
    from caqtus.experiment_control._shot_handling import ShotEventDispatcher

logger = logging.getLogger(__name__)


_T = TypeVar("_T")
_Q = ParamSpec("_Q")


class DeviceController[DeviceProxyType: DeviceProxy, **_P](abc.ABC):
    """Controls a device during a shot.

    Subclasses must implement :meth:`run_shot` to define the behavior of the associated
    device during a shot.

    This class is generic in the type of device proxy that it controls and the extra
    arguments passed to the :meth:`run_shot` method.

    Attributes:
        device_name: The name of the device being controlled.
    """

    def __init__(
        self,
        device_name: DeviceName,
        shot_event_dispatcher: "ShotEventDispatcher",
    ):
        # This method is not meant to be overridden or called directly.

        self.device_name = device_name
        self._event_dispatcher = shot_event_dispatcher
        self._signaled_ready = anyio.Event()
        self._signaled_ready_time: Optional[float] = None
        self._finished_waiting_ready_time: Optional[float] = None
        self._thread_times: list[tuple[str, float, float]] = []
        self._data_waits: list[tuple[str, float, float]] = []
        self._data_signals: list[tuple[str, float]] = []

    @abc.abstractmethod
    async def run_shot(
        self, device: DeviceProxyType, /, *args: _P.args, **kwargs: _P.kwargs
    ) -> None:
        """Runs a shot on the device.

        This method must call :meth:`wait_all_devices_ready` exactly once.

        Args:
            device: An asynchronous proxy to the device being controlled.
            args, kwargs: Extra arguments than can be computed before the shot
                and that are required to run the shot.
        """

        raise NotImplementedError

    @final
    async def _run_shot(
        self, device: DeviceProxyType, *args: _P.args, **kwargs: _P.kwargs
    ) -> ShotStats:
        start_time = self._event_dispatcher.shot_time()
        await self.run_shot(device, *args, **kwargs)
        finished_time = self._event_dispatcher.shot_time()
        if not self._signaled_ready.is_set():
            raise RuntimeError(
                f"wait_all_devices_ready was not called in run_shot for {self}"
            )
        assert self._signaled_ready_time is not None
        assert self._finished_waiting_ready_time is not None

        return ShotStats(
            start_time=start_time,
            signaled_ready_time=self._signaled_ready_time,
            finished_waiting_ready_time=self._finished_waiting_ready_time,
            finished_time=finished_time,
            thread_stats=self._thread_times,
            data_waits=self._data_waits,
            data_signals=self._data_signals,
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
        """Signals that data has been acquired from the device.

        Args:
            label: The label of the data.
            data: The data that was acquired.
        """

        self._event_dispatcher.signal_data_acquired(self.device_name, label, data)
        self._data_signals.append((label, self._event_dispatcher.shot_time()))

    @final
    async def wait_data_acquired(self, label: DataLabel) -> Data:
        """Waits until another device signals that some data has been acquired."""

        start = self._event_dispatcher.shot_time()
        data = await self._event_dispatcher.wait_data_acquired(self.device_name, label)
        end = self._event_dispatcher.shot_time()
        self._data_waits.append((label, start, end))
        return data

    def _debug_stats(self):
        return {
            "signaled_ready_time": self._signaled_ready_time,
            "finished_waiting_ready_time": self._finished_waiting_ready_time,
        }

    @final
    async def run_in_thread(
        self, func: Callable[_Q, _T], *args: _Q.args, **kwargs: _Q.kwargs
    ) -> _T:
        func_name = func.__name__
        start_time = self._event_dispatcher.shot_time()
        result = await anyio.to_thread.run_sync(
            functools.partial(func, *args, **kwargs)
        )
        end_time = self._event_dispatcher.shot_time()
        self._thread_times.append((func_name, start_time, end_time))
        return result

    @final
    async def sleep(self, seconds: float) -> None:
        """Sleeps for a given number of seconds."""

        await anyio.sleep(seconds)


class ShotStats(TypedDict):
    start_time: float
    signaled_ready_time: float
    finished_waiting_ready_time: float
    finished_time: float
    thread_stats: list[tuple[str, float, float]]
    data_waits: list[tuple[str, float, float]]
    data_signals: list[tuple[str, float]]


DeviceControllerType = TypeVar("DeviceControllerType", bound=DeviceController)
