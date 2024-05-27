from collections.abc import Mapping
from multiprocessing.managers import RemoteError
from typing import Any

from caqtus.device import DeviceName, Device, DeviceConfiguration
from caqtus.device.remote_server import DeviceServerConfiguration, RemoteDeviceManager
from caqtus.shot_compilation import (
    DeviceCompiler,
)


def create_devices(
    device_compilers: Mapping[DeviceName, DeviceCompiler],
    device_configs: Mapping[DeviceName, DeviceConfiguration],
    device_types: Mapping[DeviceName, type[Device]],
    device_server_configs: Mapping[str, DeviceServerConfiguration],
    manager_class: type[RemoteDeviceManager],
) -> dict[DeviceName, Device]:
    device_servers = create_device_servers(device_server_configs, manager_class)
    connect_to_device_servers(device_servers)

    result = {}

    for device_name, device_compiler in device_compilers.items():
        initialization_parameters = device_compiler.compile_initialization_parameters()
        device_config = device_configs[device_name]
        device_type = device_types[device_name]
        if device_config.remote_server is None:
            result[device_name] = device_type(**initialization_parameters)
        else:
            manager = device_servers[device_config.remote_server]
            result[device_name] = create_device_on_server(
                device_name, device_type.__name__, initialization_parameters, manager
            )

    return result


def create_device_servers(
    device_server_configs: Mapping[str, DeviceServerConfiguration],
    manager_class: type[RemoteDeviceManager],
) -> dict[str, RemoteDeviceManager]:
    device_servers: dict[str, RemoteDeviceManager] = {}
    for server_name, server_config in device_server_configs.items():
        address = (server_config.address, server_config.port)
        authkey = bytes(server_config.authkey.get_secret_value(), encoding="utf-8")
        device_servers[server_name] = manager_class(
            address=address,
            authkey=authkey,
        )
    return device_servers


def connect_to_device_servers(
    device_servers: Mapping[str, RemoteDeviceManager]
) -> None:
    """Start the connection to the device servers."""

    for server_name, server in device_servers.items():
        try:
            server.connect()
        except ConnectionRefusedError as error:
            raise ConnectionRefusedError(
                f"The remote server '{server_name}' rejected the connection. It is"
                " possible that the server is not running or that the port is not"
                " open."
            ) from error
        except TimeoutError as error:
            raise TimeoutError(
                f"The remote server '{server_name}' did not respond to the"
                " connection request. It is possible that the server is not"
                " running or that the port is not open."
            ) from error


def create_device_on_server(
    device_name: DeviceName,
    device_type: str,
    init_params: Mapping[str, Any],
    manager: RemoteDeviceManager,
) -> Device:
    """Create a device on its remote server."""

    try:
        remote_class = getattr(manager, device_type)
    except AttributeError:
        raise ValueError(
            f"The device '{device_name}' is of type '{device_type}' but"
            " this type is not registered for the remote device client."
        )

    try:
        return remote_class(**init_params)
    except RemoteError as error:
        raise RuntimeError(
            f"Remote servers {manager} could not instantiate device '{device_name}'"
        ) from error
