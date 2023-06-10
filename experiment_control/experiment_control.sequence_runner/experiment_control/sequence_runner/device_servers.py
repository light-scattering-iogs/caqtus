import logging
from typing import Mapping

from experiment.configuration import DeviceServerConfiguration
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
