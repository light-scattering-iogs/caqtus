import abc
import concurrent.futures
import contextlib
from collections.abc import Mapping
from typing import Protocol, Any

from core.device import DeviceName, DeviceParameter, DeviceConfigurationAttrs, Device
from core.session.shot import TimeLanes
from core.types.data import DataLabel, Data
from util.concurrent import TaskGroup


class ShotRunner(abc.ABC):
    def __init__(self, devices: Mapping[DeviceName, Device]):
        self.devices = dict(devices)
        self.exit_stack = contextlib.ExitStack()
        self.thread_pool = concurrent.futures.ThreadPoolExecutor()

    def __enter__(self):
        """Initialize the shot runner.

        The shot runner must initialize itself and acquire all necessary resources here.
        After this method is called, the shot runner must be ready to run shots.

        Typically, this method will initialize the required devices.

        The base class implementation of this method enters its exit stack, initializes a thread pool, and enters the
        context of each device.
        """

        self.exit_stack.__enter__()
        self.exit_stack.enter_context(self.thread_pool)
        try:
            for device in self.devices.values():
                self.exit_stack.enter_context(device)
        except Exception as e:
            self.exit_stack.__exit__(type(e), e, e.__traceback__)
            raise
        return self

    @abc.abstractmethod
    def run_shot(
        self, device_parameters: Mapping[DeviceName, Mapping[DeviceParameter, Any]]
    ) -> Mapping[DataLabel, Data]:
        """Run the shot."""

        raise NotImplementedError

    def update_device_parameters(
        self, device_parameters: Mapping[DeviceName, Mapping[DeviceParameter, Any]]
    ):
        with TaskGroup(self.thread_pool, name="update devices") as g:
            for device_name, parameters in device_parameters.items():
                g.create_task(
                    update_device, device_name, self.devices[device_name], parameters
                )

    def __exit__(self, exc_type, exc_value, traceback):
        """All device cleanups must be done here."""

        self.exit_stack.__exit__(exc_type, exc_value, traceback)


def update_device(name: str, device: Device, parameters: Mapping[str, Any]):
    try:
        if parameters:
            device.update_parameters(**parameters)
    except Exception as error:
        raise RuntimeError(f"Failed to update device {name}") from error


class ShotRunnerFactory(Protocol):
    def __call__(
        self,
        shot_timelanes: TimeLanes,
        device_configurations: Mapping[DeviceName, DeviceConfigurationAttrs],
    ) -> ShotRunner:
        ...
