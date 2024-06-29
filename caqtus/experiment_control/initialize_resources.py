import contextlib
from collections.abc import Iterable, Mapping
from typing import Any

from ._initialize_devices import create_devices
from ._shot_handling import ShotRunner, ShotCompiler
from .device_manager_extension import DeviceManagerExtensionProtocol
from ..device import DeviceName, DeviceConfiguration
from ..device.remote import DeviceProxy
from ..shot_compilation import SequenceContext, DeviceCompiler, DeviceNotUsedException
from ..types.timelane import TimeLanes


@contextlib.asynccontextmanager
async def create_shot_resources(
    initial_sequence_context: SequenceContext,
    device_manager_extension: DeviceManagerExtensionProtocol,
):
    """Creates and acquires resources for running a shot.

    Returns:
        A context manager that yields a shot compiler and a shot runner.
    """

    device_compilers = create_device_compilers(
        initial_sequence_context, device_manager_extension
    )
    device_types = get_device_types(
        device_compilers.keys(), initial_sequence_context, device_manager_extension
    )
    in_use_configurations = {
        device_name: initial_sequence_context.get_device_configuration(device_name)
        for device_name in device_compilers
    }
    async with create_devices(
        device_compilers=device_compilers,
        device_configs=in_use_configurations,
        device_types=device_types,
        device_manager_extension=device_manager_extension,
    ) as devices_in_use:
        shot_runner = _create_shot_runner(
            device_proxies=devices_in_use,
            device_configurations=in_use_configurations,
            device_manager_extension=device_manager_extension,
        )
        shot_compiler = _create_shot_compiler(
            time_lanes=initial_sequence_context._time_lanes,  # noqa
            device_configurations=in_use_configurations,
            device_compilers=device_compilers,
        )
        yield shot_compiler, shot_runner


def create_device_compilers(
    sequence_context: SequenceContext,
    device_manager_extension: DeviceManagerExtensionProtocol,
) -> dict[DeviceName, DeviceCompiler]:
    device_compilers = {}
    for (
        device_name,
        device_configuration,
    ) in sequence_context.get_all_device_configurations().items():
        compiler_type = device_manager_extension.get_device_compiler_type(
            device_configuration
        )
        try:
            compiler = compiler_type(device_name, sequence_context)
        except DeviceNotUsedException:
            continue
        else:
            device_compilers[device_name] = compiler
    return device_compilers


def get_device_types(
    devices: Iterable[DeviceName],
    sequence_context: SequenceContext,
    device_manager_extension: DeviceManagerExtensionProtocol,
) -> dict[DeviceName, Any]:
    device_types = {
        device_name: device_manager_extension.get_device_type(
            sequence_context.get_device_configuration(device_name)
        )
        for device_name in devices
    }
    return device_types


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


def _create_shot_compiler(
    time_lanes: TimeLanes,
    device_configurations: Mapping[DeviceName, DeviceConfiguration],
    device_compilers: Mapping[DeviceName, DeviceCompiler],
) -> ShotCompiler:
    shot_compiler = ShotCompiler(
        time_lanes,
        device_configurations=device_configurations,
        device_compilers=device_compilers,
    )
    return shot_compiler
