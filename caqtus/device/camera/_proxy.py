import contextlib
from typing import TypeVar

import eliot

from caqtus.device.remote import DeviceProxy
from ._runtime import Camera

CameraType = TypeVar("CameraType", bound=Camera)


class CameraProxy(DeviceProxy[CameraType]):
    async def update_parameters(self, timeout: float, *args, **kwargs) -> None:
        return await self.call_method("update_parameters", timeout, *args, **kwargs)

    @contextlib.asynccontextmanager
    async def acquire(self, exposures: list[float]):
        async with (
            self.call_method_proxy_result("acquire", exposures) as cm_proxy,
            self.async_context_manager(cm_proxy) as iterator_proxy,
        ):
            yield self.async_iterator(iterator_proxy)
            return
