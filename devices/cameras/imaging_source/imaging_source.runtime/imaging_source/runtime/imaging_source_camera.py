"""
Imaging Source camera runtime class.

Note that to import this package, the library tisgrabber_x64.dll must be installed
"""

import ctypes
import logging
import os
import pathlib
import shutil
import threading
from tempfile import mkdtemp

import numpy
from pydantic import Field

from camera.runtime import CCamera
from .tisgrabber import declareFunctions, D, T, HGRABBER, IC_SUCCESS

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

tisgrabber_path = (
    os.path.expanduser("~")
    + "\\Documents\\The Imaging Source Europe GmbH\\TIS Grabber DLL\\bin\\x64\\tisgrabber_x64.dll"
)

ic = ctypes.cdll.LoadLibrary(tisgrabber_path)
declareFunctions(ic)

ic.IC_InitLibrary(0)


class ImagingSourceCamera(CCamera):

    camera_name: str = Field(description="The name of the camera", allow_mutation=False)

    _grabber_handle: ctypes.POINTER(HGRABBER) = None
    _acquisition_thread: threading.Thread = None
    _temp_dir: pathlib.Path = None
    _settings_file: pathlib.Path = None

    def start(self):
        self._grabber_handle = ic.IC_CreateGrabber()
        ic.IC_OpenDevByUniqueName(self._grabber_handle, T(self.camera_name))
        if not ic.IC_IsDevValid(self._grabber_handle):
            raise RuntimeError(f"{self.name}: camera {self.camera_name} not found")

        self._temp_dir = pathlib.Path(mkdtemp())
        self._settings_file = self._temp_dir / "settings.xml"
        self.save_state_to_file(self._settings_file)

        self.reset_properties()

        self.update_parameters(exposures=self.exposures)

    def shutdown(self):
        self.load_state_from_file(self._settings_file)
        try:
            shutil.rmtree(self._temp_dir)
        except Exception as error:
            logger.warning(
                f"Could not remove temporary directory {self._temp_dir}: {error}"
            )

        try:
            if self._grabber_handle is not None:
                ic.IC_StopLive(self._grabber_handle)
                ic.IC_ReleaseGrabber(self._grabber_handle)
        finally:
            super().shutdown()

    def update_parameters(self, /, exposures: list[float]) -> None:
        """Update the exposures time of the camera"""

        all_acquisitions_equal = all(exposures[0] == exposure for exposure in exposures)

        if not all_acquisitions_equal:
            raise NotImplementedError(
                f"Camera {self.name} does not support changing exposure"
            )

        super().update_parameters(exposures=exposures)
        exposure = self.exposures[0]
        self.set_exposure(exposure)

    def set_exposure(self, exposure: float):
        return
        ic.IC_SetExposureTime(self._grabber_handle, D(exposure))

    def _start_acquisition(self):
        ic.IC_StartLive(self._grabber_handle, 0)

        def acquire_pictures():
            for picture_number in range(self.number_pictures_to_acquire):
                self._snap_picture(picture_number, self.timeout)
                image = self._read_picture_from_camera()
                self._pictures[picture_number] = image

        self._acquisition_thread = threading.Thread(target=acquire_pictures)
        self._acquisition_thread.start()

    def _is_acquisition_in_progress(self) -> bool:
        return self._acquisition_thread.is_alive()

    def _stop_acquisition(self):
        self._acquisition_thread.join()
        ic.IC_StopLive(self._grabber_handle)

    def _snap_picture(self, picture_number: int, timeout: float) -> None:
        result = ic.IC_SnapImage(self._grabber_handle, int(timeout * 1e3))
        if result == IC_SUCCESS:
            logger.info(f"Picture {picture_number} acquired")
        else:
            raise RuntimeError("Failed to acquire picture")

    def _read_picture_from_camera(self) -> numpy.ndarray:
        width = ctypes.c_long()
        height = ctypes.c_long()
        bits_per_pixel = ctypes.c_int()
        color_format = ctypes.c_int()

        ic.IC_GetImageDescription(
            self._grabber_handle, width, height, bits_per_pixel, color_format
        )

        buffer_size = width.value * height.value * bits_per_pixel.value

        image_ptr = ic.IC_GetImagePtr(self._grabber_handle)

        data = ctypes.cast(image_ptr, ctypes.POINTER(ctypes.c_ubyte * buffer_size))

        bytes_per_pixel = int(bits_per_pixel.value / 8.0)
        image = numpy.ndarray(
            buffer=data.contents,
            dtype=numpy.uint8,
            shape=(height.value, width.value, bytes_per_pixel),
        )
        return image

    @classmethod
    def get_device_counts(cls) -> int:
        return ic.IC_GetDeviceCount()

    @classmethod
    def get_device_names(cls) -> list[str]:
        return [
            D(ic.IC_GetUniqueNamefromList(i)) for i in range(cls.get_device_counts())
        ]

    def save_state_to_file(self, file):
        ic.IC_SaveDeviceStateToFile(self._grabber_handle, T(str(file)))

    def load_state_from_file(self, file):
        ic.IC_LoadDeviceStateFromFile(self._grabber_handle, T(str(file)))

    def reset_properties(self):
        ic.IC_ResetProperties(self._grabber_handle)
