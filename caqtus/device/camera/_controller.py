import eliot

from caqtus.device.controller import (
    DeviceController,
)
from caqtus.types.data import DataLabel
from ._proxy import CameraProxy


class CameraController(DeviceController):
    async def run_shot(
        self,
        camera: CameraProxy,
        /,
        timeout: float,
        picture_names: list[str],
        exposures: list[float],
        *args,
        **kwargs,
    ) -> None:
        if len(picture_names) != len(exposures):
            raise ValueError(
                f"Number of picture names ({len(picture_names)}) must be equal to the "
                f"number of exposures ({len(exposures)})"
            )
        await camera.update_parameters(timeout=timeout, *args, **kwargs)
        async with camera.acquire(exposures) as pictures:
            await self.wait_all_devices_ready()
            current_picture = 0
            async for picture in pictures:
                picture_name = picture_names[current_picture]
                label = DataLabel(rf"{self.device_name}\{picture_name}")
                self.signal_data_acquired(
                    label,
                    picture,
                )
                current_picture += 1
