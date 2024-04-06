from caqtus.device.controller import (
    DeviceController,
    run_in_thread,
    async_context,
    iterate_async,
)
from caqtus.types.data import DataLabel
from ._runtime import Camera


class CameraController(DeviceController[Camera]):
    async def run_shot(
        self,
        camera: Camera,
        /,
        timeout: float,
        picture_names: list[str],
        exposures: list[float],
    ) -> None:
        await run_in_thread(camera.update_parameters, timeout=timeout)

        async with async_context(camera.acquire(exposures)) as pictures:
            self.signal_ready()
            async for name, picture in iterate_async(
                zip(picture_names, pictures, strict=True)
            ):
                self.signal_data_acquired(
                    DataLabel(rf"{self.device_name}\{name}"), picture
                )
