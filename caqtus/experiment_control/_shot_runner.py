from __future__ import annotations

import contextlib
from collections.abc import Callable, AsyncGenerator
from collections.abc import Mapping
from typing import Protocol

from caqtus.device import DeviceController
from caqtus.types.data import DataLabel, Data
from ._initialize_devices import create_devices
from ._shot_compiler import ShotCompilerProtocol
from ._shot_event_dispatcher import DeviceRunConfig, ShotEventDispatcher
from ._shot_primitives import DeviceParameters
from .device_manager_extension import DeviceManagerExtensionProtocol
from ..device import DeviceName, DeviceConfiguration
from ..device.remote import DeviceProxy
from ..shot_compilation import SequenceContext


class ShotRunnerProtocol(Protocol):
    """Interface for running a shot."""

    async def run_shot(
        self, shot_parameters: DeviceParameters
    ) -> Mapping[DataLabel, Data]:
        """Run a shot.

        Args:
            shot_parameters: The parameters for the shot.
        """

        ...


type ShotRunnerFactory = Callable[
    [SequenceContext, ShotCompilerProtocol, DeviceManagerExtensionProtocol],
    contextlib.AbstractAsyncContextManager[ShotRunnerProtocol, None],
]
"""A function called to create a object that can run a shot."""


class ShotRunner(ShotRunnerProtocol):
    def __init__(
        self,
        devices: Mapping[DeviceName, DeviceProxy],
        controller_types: Mapping[DeviceName, type[DeviceController]],
    ):
        if set(devices.keys()) != set(controller_types.keys()):
            raise ValueError("The devices and controller_types must have the same keys")
        self.devices = devices
        self.controller_types = controller_types

    async def run_shot(
        self,
        shot_params: DeviceParameters,
    ) -> Mapping[DataLabel, Data]:
        event_dispatcher = ShotEventDispatcher(
            {
                name: DeviceRunConfig(
                    device=self.devices[name],
                    controller_type=self.controller_types[name],
                    parameters=shot_params.device_parameters[name],
                )
                for name in self.devices
            }
        )
        return await event_dispatcher.run_shot(shot_params.timeout)


@contextlib.asynccontextmanager
async def create_shot_runner(
    sequence_context: SequenceContext,
    shot_compiler: ShotCompilerProtocol,
    device_manager_extension: DeviceManagerExtensionProtocol,
) -> AsyncGenerator[ShotRunner, None]:
    """Creates and acquires resources for running a shot.

    Returns:
        A context manager that yields a shot runner.
    """

    initialization_parameters = shot_compiler.compile_initialization_parameters()

    device_configurations_in_use = {
        name: sequence_context.get_device_configuration(name)
        for name in initialization_parameters
    }

    device_types = {
        name: device_manager_extension.get_device_type(config)
        for name, config in device_configurations_in_use.items()
    }

    async with create_devices(
        initialization_parameters=initialization_parameters,
        device_configs=device_configurations_in_use,
        device_types=device_types,
        device_manager_extension=device_manager_extension,
    ) as devices_in_use:
        shot_runner = _create_shot_runner(
            device_proxies=devices_in_use,
            device_configurations=device_configurations_in_use,
            device_manager_extension=device_manager_extension,
        )

        yield shot_runner


def _create_shot_runner(
    device_proxies: Mapping[DeviceName, DeviceProxy],
    device_configurations: Mapping[DeviceName, DeviceConfiguration],
    device_manager_extension: DeviceManagerExtensionProtocol,
) -> ShotRunner:
    device_controller_types = {
        name: device_manager_extension.get_device_controller_type(
            device_configurations[name]
        )
        for name in device_proxies
    }
    shot_runner = ShotRunner(device_proxies, device_controller_types)
    return shot_runner
