import contextlib
from collections.abc import Mapping, AsyncGenerator, Callable
from typing import TypeVar

import anyio

from caqtus.device import DeviceName, Device, DeviceConfiguration
from caqtus.device.remote import Client, DeviceProxy, RPCConfiguration
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
    device_types: Mapping[DeviceName, Callable[..., Device]],
    device_manager_extension: DeviceManagerExtensionProtocol,
) -> AsyncGenerator[dict[DeviceName, DeviceProxy], None]:
    device_server_configs = {}
    for device_config in device_configs.values():
        remote_server = device_config.remote_server
        if remote_server is not None:
            device_server_configs[remote_server] = (
                device_manager_extension.get_device_server_config(remote_server)
            )

    async with create_rpc_clients(device_server_configs) as rpc_clients:
        uninitialized_proxies = {}
        for device_name, device_compiler in device_compilers.items():
            init_params = device_compiler.compile_initialization_parameters()
            device_config = device_configs[device_name]
            device_type = device_types[device_name]
            if device_config.remote_server is None:
                raise NotImplementedError
            client = rpc_clients[device_config.remote_server]
            proxy_type = device_manager_extension.get_proxy_type(device_config)
            device_proxy = proxy_type(client, device_type, **init_params)
            uninitialized_proxies[device_name] = device_proxy
        async with context_group(uninitialized_proxies) as devices:
            yield devices


@contextlib.asynccontextmanager
async def create_rpc_clients(
    device_server_configs: Mapping[str, RPCConfiguration],
) -> AsyncGenerator[dict[str, Client], None]:
    clients: dict[str, Client] = {}
    async with contextlib.AsyncExitStack() as stack:
        for server_name, config in device_server_configs.items():
            client = Client(config)
            await stack.enter_async_context(client)
            clients[server_name] = client
        yield clients


T = TypeVar("T")


async def enter_and_push(
    stack: contextlib.AsyncExitStack,
    key: str,
    cm: contextlib.AbstractAsyncContextManager[T],
    results: dict,
):
    value = await stack.enter_async_context(cm)
    results[key] = value


@contextlib.asynccontextmanager
async def context_group(
    cms: Mapping[str, contextlib.AbstractAsyncContextManager[T]]
) -> AsyncGenerator[Mapping[str, T], None]:
    results = {}
    async with contextlib.AsyncExitStack() as stack:
        async with anyio.create_task_group() as tg:
            for key, cm in cms.items():
                tg.start_soon(enter_and_push, stack, key, cm, results)
        yield results
