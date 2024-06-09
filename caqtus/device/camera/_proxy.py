import contextlib
from collections.abc import AsyncGenerator, AsyncIterable
from typing import TypeVar

from caqtus.device.remote import DeviceProxy
from caqtus.types.image import Image
from ._runtime import Camera
from ..remote.rpc.server import RemoteError

CameraType = TypeVar("CameraType", bound=Camera)


class CameraProxy(DeviceProxy[CameraType]):
    async def update_parameters(self, timeout: float, *args, **kwargs) -> None:
        return await self.call_method("update_parameters", timeout, *args, **kwargs)

    @contextlib.asynccontextmanager
    async def acquire(
        self, exposures: list[float]
    ) -> AsyncGenerator[AsyncIterable[Image], None, None]:
        async with self.call_method_proxy_result(
            "acquire", exposures
        ) as cm_proxy, self.async_context_manager(cm_proxy) as iterator_proxy:
            try:
                yield self._rpc_client.async_iterator(iterator_proxy)
                return
            except RemoteError as e:
                if isinstance(e.__cause__, Exception):
                    # We unwrap the remote exception to get the original exception, that
                    # could for example be a timeout from the camera.
                    error = e.__cause__
                else:
                    error = e
            raise error
