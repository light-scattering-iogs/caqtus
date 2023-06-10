import logging
from multiprocessing.managers import RemoteError
from typing import Mapping

from device.configuration import DeviceName
from device.runtime import RuntimeDevice
from experiment.configuration import DeviceServerConfiguration
from experiment_control.compute_device_parameters.initialize_devices import (
    InitializationParameters,
)
from remote_device_client import RemoteDeviceClientManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def create_device_servers(
    device_server_configs: Mapping[str, DeviceServerConfiguration]
) -> dict[str, RemoteDeviceClientManager]:
    device_servers: dict[str, RemoteDeviceClientManager] = {}
    for server_name, server_config in device_server_configs.items():
        address = (server_config.address, server_config.port)
        authkey = bytes(server_config.authkey.get_secret_value(), encoding="utf-8")
        device_servers[server_name] = RemoteDeviceClientManager(
            address=address, authkey=authkey
        )
    return device_servers


def connect_to_device_servers(
    device_servers: Mapping[str, RemoteDeviceClientManager],
    mock_experiment: bool = False,
) -> None:
    """Start the connection to the device servers."""

    if mock_experiment:
        return

    for server_name, server in device_servers.items():
        logger.info(f"Connecting to device server {server_name}...")
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
        logger.info(f"Connection established to {server_name}")


def create_devices(
    initialization_parameters: Mapping[DeviceName, InitializationParameters],
    remote_device_servers: Mapping[str, RemoteDeviceClientManager],
    mock_experiment: bool = False,
) -> dict[DeviceName, RuntimeDevice]:
    """Instantiate the devices on their respective remote server.

    This function instantiate the device objects according to their parameters on their respective device servers. The
    device objects are then returned as a dictionary matching the device names to a proxy to the associated device.

    This function only creates the device objects but does not start them. No communication with the actual devices
    is performed at this stage.
    """

    if mock_experiment:
        return {}

    devices: dict[DeviceName, RuntimeDevice] = {}

    for device_name, parameters in initialization_parameters.items():
        server = remote_device_servers[parameters["server"]]
        try:
            remote_class = getattr(server, parameters["type"])
        except AttributeError:
            raise ValueError(
                f"The device '{device_name}' is of type '{parameters['type']}' but"
                " this type is not registered for the remote device client."
            )

        try:
            init_kwargs = parameters["init_kwargs"]
            if "name" not in init_kwargs:
                init_kwargs["name"] = device_name
            devices[device_name] = remote_class(**init_kwargs)
        except RemoteError as error:
            raise RuntimeError(
                f"Remote servers {parameters['server']} could not instantiate"
                f" device '{device_name}'"
            ) from error

    return devices
