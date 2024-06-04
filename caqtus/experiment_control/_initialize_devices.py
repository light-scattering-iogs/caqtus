import contextlib
from collections.abc import Mapping, AsyncGenerator

from caqtus.device import DeviceName, Device, DeviceConfiguration
from caqtus.device.remote import Client
from caqtus.device.remote_server import DeviceServerConfiguration
from caqtus.experiment_control.device_manager_extension import (
    DeviceManagerExtensionProtocol,
)
from caqtus.shot_compilation import (
    DeviceCompiler,
)


@contextlib.asynccontextmanager
async def create_devices(
    device_compilers: Mapping[DeviceName, DeviceCompiler],
    device_configs: Mapping[DeviceName, DeviceConfiguration],
    device_types: Mapping[DeviceName, type[Device]],
    device_manager_extension: DeviceManagerExtensionProtocol,
) -> AsyncGenerator[dict[DeviceName, Device], None]:
    device_server_configs = {}
    for device_config in device_configs.values():
        remote_server = device_config.remote_server
        if remote_server is not None:
            device_server_configs[remote_server] = (
                device_manager_extension.get_device_server_config(remote_server)
            )

    async with create_rpc_clients(
        device_server_configs
    ) as rpc_clients, contextlib.AsyncExitStack() as stack:
        result = {}
        for device_name, device_compiler in device_compilers.items():
            init_params = device_compiler.compile_initialization_parameters()
            device_config = device_configs[device_name]
            device_type = device_types[device_name]
            if device_config.remote_server is None:
                raise NotImplementedError
            client = rpc_clients[device_config.remote_server]
            proxy_type = device_manager_extension.get_proxy_type(device_type)
            device_proxy = proxy_type(client, device_type, **init_params)
            await stack.enter_async_context(device_proxy)
            result[device_name] = device_type(device_proxy)
        yield result


@contextlib.asynccontextmanager
async def create_rpc_clients(
    device_server_configs: Mapping[str, DeviceServerConfiguration],
) -> AsyncGenerator[dict[str, Client], None]:
    clients: dict[str, Client] = {}
    async with contextlib.AsyncExitStack() as stack:
        for server_name, server_config in device_server_configs.items():
            client = Client(
                target=server_config.target, credentials=server_config.credentials
            )
            await stack.enter_async_context(client)
            clients[server_name] = client
        yield clients
