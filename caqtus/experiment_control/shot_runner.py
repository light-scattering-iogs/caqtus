import abc
import contextlib
from collections.abc import Mapping
from typing import Protocol, Any

import anyio
import anyio.to_thread

from caqtus.device import DeviceName, DeviceParameter, DeviceConfiguration, Device
from caqtus.session.shot import TimeLanes
from caqtus.types.data import DataLabel, Data


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
        After this method is called, the shot runner must be ready to have its
        :meth:`run_shot` method called.

        Typically, this method will initialize the required devices.

        The base class implementation of this method enters the context of all devices
        concurrently and pushes them to the exit stack.
        """

        self.exit_stack.__enter__()
        try:
            anyio.run(self._enter_async, backend="trio")
        except Exception as e:
            # If an error occurs while initializing a device, we close the exit stack to
            # ensure that all devices are exited.
            self.exit_stack.__exit__(type(e), e, e.__traceback__)
            raise
        return self

    async def _enter_async(self):
        async with anyio.create_task_group() as tg:
            for device in self.devices.values():
                tg.start_soon(self._enter_device, device)

    async def _enter_device(self, device: Device) -> None:
        with anyio.CancelScope(shield=True):
            await anyio.to_thread.run_sync(device.__enter__)
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
    ) -> None:
        """Update the parameters of the devices.

        This method calls the :meth:`Device.update_parameters` method of each device
        with the provided parameters.

        The default implementation updates devices concurrently in separate threads to
        reduce the total update time.

        Args:
            device_parameters: A mapping matching device names to the parameters that
            should be updated for each device.
            The device names in the mapping must be a subset of the device names
            provided to the shot runner at initialization.

        Raises:
            KeyError: If a device name in the mapping is not present in the shot runner
            devices.
            ExceptionGroup: If errors occur while updating some devices, they are
            raised inside an exception group.
        """

        anyio.run(
            self._update_device_parameters_async, device_parameters, backend="trio"
        )

    async def _update_device_parameters_async(
        self, device_parameters: Mapping[DeviceName, Mapping[DeviceParameter, Any]]
    ):
        async with anyio.create_task_group() as tg:
            for name, parameters in device_parameters.items():
                device = self.devices[name]
                tg.start_soon(
                    anyio.to_thread.run_sync, update_device, name, device, parameters
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
        device_configurations: Mapping[DeviceName, DeviceConfiguration],
    ) -> ShotRunner:
        ...
