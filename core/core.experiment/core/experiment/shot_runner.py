import abc
import asyncio
import contextlib
from collections.abc import Mapping
from typing import Protocol, Any

import util.concurrent
from core.device import DeviceName, DeviceParameter, DeviceConfigurationAttrs, Device
from core.session.shot import TimeLanes
from core.types.data import DataLabel, Data


class ShotRunner(abc.ABC):
    """Shot runners are responsible for running shots on the experiment.

    This is an abstract base class.
    It provides common functionality for managing devices within a shot.
    It is meant to be subclassed for specific setups that must implement the
    :meth:`ShotRunner.run_shot` method.
    """

    def __init__(self, devices: Mapping[DeviceName, Device]):
        """Initialize the shot runner.

        Args:
            devices: A mapping containing the devices that the shot runner will use to
            run shots.
            The devices are not initialized yet.
            They will be initialized when the shot runner is entered.
        """

        self.devices = dict(devices)
        self.exit_stack = contextlib.ExitStack()

    def __enter__(self):
        """Prepares the shot runner.

        The shot runner must initialize itself and acquire all necessary resources here.
        After this method is called, the shot runner must be ready to run shots.

        Typically, this method will initialize the required devices.

        The base class implementation of this method enters the context of all devices
        concurrently and pushes them to the exit stack.
        """

        self.exit_stack.__enter__()
        try:
            asyncio.run(self._enter_async())
        except Exception as e:
            # If an error occurs while initializing a device, we close the exit stack to
            # ensure that all devices are exited.
            self.exit_stack.__exit__(type(e), e, e.__traceback__)
            raise
        return self

    async def _enter_async(self):
        # If a device raises an exception during initialization, it will not cancel the
        # initialization of the other devices.
        # This prevents a device from being entered without being pushed to the exit
        # stack.
        exceptions = await asyncio.gather(
            *[self._enter_device(device) for device in self.devices.values()],
            return_exceptions=True,
        )
        exceptions = [e for e in exceptions if e is not None]
        if exceptions:
            raise ExceptionGroup(
                "Errors occurred while initializing devices", exceptions
            )

    async def _enter_device(self, device: Device) -> None:
        await asyncio.to_thread(device.__enter__)
        self.exit_stack.push(device)

    @abc.abstractmethod
    def run_shot(
        self, device_parameters: Mapping[DeviceName, Mapping[DeviceParameter, Any]]
    ) -> Mapping[DataLabel, Data]:
        """Run the shot.

        This is the main method of the shot runner.
        """

        raise NotImplementedError

    def update_device_parameters(
        self, device_parameters: Mapping[DeviceName, Mapping[DeviceParameter, Any]]
    ):
        """Update the parameters of the devices.

        This method calls the :meth:`Device.update_parameters` method of each device
        with the provided parameters.

        Args:
            device_parameters: A mapping matching device names to the parameters that
            should be updated for each device.
            The device names in the mapping must be a subset of the device names
            provided to the shot runner at initialization.
        """

        with util.concurrent.TaskGroup() as group:
            for name, parameters in device_parameters.items():
                group.create_task(update_device, name, self.devices[name], parameters)

        asyncio.run(self._update_device_parameters_async(device_parameters))

    async def _update_device_parameters_async(
        self, device_parameters: Mapping[DeviceName, Mapping[DeviceParameter, Any]]
    ):
        # We don't use a TaskGroup here because if a device fails, it will cancel the
        # other tasks, without verifying that the operations in threads are finished.
        potential_exceptions = await asyncio.gather(
            *[
                asyncio.to_thread(update_device, name, self.devices[name], parameters)
                for name, parameters in device_parameters.items()
            ],
            return_exceptions=True,
        )
        exceptions = [e for e in potential_exceptions if e is not None]
        if exceptions:
            raise ExceptionGroup(
                "Errors occurred while updating device parameters", exceptions
            )

    def __exit__(self, exc_type, exc_value, traceback):
        """Shutdown the shot runner.

        The shot runner must release all resources that it has acquired here.

        The base class implementation of this method closes its exit stack, thus
        exiting the context of each device.
        """

        self.exit_stack.__exit__(exc_type, exc_value, traceback)


def update_device(
    name: str, device: Device, parameters: Mapping[DeviceParameter, Any]
) -> None:
    try:
        if parameters:
            device.update_parameters(**parameters)  # type: ignore
    except Exception as error:
        raise RuntimeError(f"Failed to update device {name}") from error


class ShotRunnerFactory(Protocol):
    def __call__(
        self,
        shot_timelanes: TimeLanes,
        device_configurations: Mapping[DeviceName, DeviceConfigurationAttrs],
    ) -> ShotRunner:
        ...
