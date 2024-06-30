import contextlib
from collections.abc import AsyncGenerator, AsyncIterable
from typing import TypeVar

import eliot

from caqtus.device.remote import DeviceProxy
from caqtus.types.image import Image
from ._runtime import Camera
from ..remote.rpc._server import RemoteError

CameraType = TypeVar("CameraType", bound=Camera)


class CameraProxy(DeviceProxy[CameraType]):
    @eliot.log_call(include_args=["timeout"], include_result=False)
    async def update_parameters(self, timeout: float, *args, **kwargs) -> None:
        return await self.call_method("update_parameters", timeout, *args, **kwargs)

    @contextlib.asynccontextmanager
    async def acquire(
        self, exposures: list[float]
    ) -> AsyncGenerator[AsyncIterable[Image], None]:
        with eliot.start_action(action_type="acquire", exposures=exposures):
            async with self.call_method_proxy_result(
                "acquire", exposures
            ) as cm_proxy, self.async_context_manager(cm_proxy) as iterator_proxy:
                try:
                    yield self._rpc_client.async_iterator(iterator_proxy)
                    return
                except RemoteError as e:
                    if e.__cause__:
                        # We unwrap the remote exception to get the original exception,
                        # that could for example be a timeout from the camera.
                        raise e.__cause__ from None
                    else:
                        # In principle there should always be a cause, but we handle the
                        # case where there isn't one just in case.
                        raise e from None
