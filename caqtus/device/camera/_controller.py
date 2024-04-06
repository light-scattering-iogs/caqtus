import dataclasses

from caqtus.device.controller import (
    DeviceController,
    run_in_thread,
    async_context,
    iterate_async,
)
from caqtus.types.data import DataLabel
from ._runtime import Camera


class CameraShotParameters(dataclasses.dataclass):
    timeout: float
    picture_names: list[str]
    exposures: list[float]


class CameraController(DeviceController[Camera]):
    async def run_shot(
        self, device: Camera, shot_parameters: CameraShotParameters
    ) -> None:
        await run_in_thread(device.update_parameters, timeout=shot_parameters.timeout)

        async with async_context(device.acquire(shot_parameters.exposures)) as pictures:
            self.signal_ready()
            async for name, picture in iterate_async(
                zip(shot_parameters.picture_names, pictures, strict=True)
            ):
                self.signal_data_acquired(
                    DataLabel(rf"{self.device_name}\{name}"), picture
                )
