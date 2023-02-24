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
from abc import ABC, abstractmethod
from tempfile import mkdtemp
from typing import Literal

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

_MAP_FORMAT = {"Y16": 4, "Y800": 0}


def _reformat_image(image: numpy.ndarray, format_: str) -> numpy.ndarray:
    height, width, bytes_per_pixel = image.shape
    if format_ == "Y16":
        new_image = numpy.zeros((height, width), dtype=numpy.uint16)
        new_image[:, :] = image[:, :, 0] + image[:, :, 1] * 256
    elif format_ == "Y800":
        new_image = numpy.zeros((height, width), dtype=numpy.uint8)
        new_image[:, :] = image[:, :, 0]
    else:
        raise NotImplementedError(f"Format {format_} not implemented")
    return new_image


class ImagingSourceCamera(CCamera, ABC):

    camera_name: str = Field(description="The name of the camera", allow_mutation=False)
    format: Literal["Y16", "Y800"] = Field(allow_mutation=False)

    _grabber_handle: ctypes.POINTER(HGRABBER) = None
    _acquisition_thread: threading.Thread = None
    _temp_dir: pathlib.Path = None
    _settings_file: pathlib.Path = None

    def start(self):
        super().start()
        self._grabber_handle = ic.IC_CreateGrabber()
        ic.IC_OpenDevByUniqueName(self._grabber_handle, T(self.camera_name))
        if not ic.IC_IsDevValid(self._grabber_handle):
            raise RuntimeError(f"{self.name}: camera {self.camera_name} not found")

        logger.info(f"{self.name}: camera {self.camera_name} found")

        self._temp_dir = pathlib.Path(mkdtemp())
        self._settings_file = self._temp_dir / "settings.xml"
        self.save_state_to_file(self._settings_file)

        # self.reset_properties()

        self._setup_properties()
        self._setup_trigger()

        self.update_parameters(exposures=self.exposures, timeout=self.timeout)

    @abstractmethod
    def _setup_properties(self):
        """Set up the properties of the camera after their reinitialization"""
        ...

    def _setup_trigger(self):
        if ic.IC_EnableTrigger(self._grabber_handle, int(self.external_trigger)) != IC_SUCCESS:
            raise RuntimeError(f"{self.name}: failed to set trigger mode")
        logger.debug(f"{self.name}: trigger mode set to {self.external_trigger}")

    def shutdown(self):
        try:
            self.load_state_from_file(self._settings_file)
            shutil.rmtree(self._temp_dir)
        except Exception as error:
            logger.warning(error)

        try:
            if self._grabber_handle is not None:
                ic.IC_StopLive(self._grabber_handle)
                ic.IC_ReleaseGrabber(self._grabber_handle)
        finally:
            super().shutdown()

    def update_parameters(self, exposures: list[float], timeout: float) -> None:
        """Update the exposures time of the camera"""

        all_acquisitions_equal = all(exposures[0] == exposure for exposure in exposures)
        logger.debug(f"{self.name}: all_acquisitions_equal = {all_acquisitions_equal}")

        if not all_acquisitions_equal:
            raise NotImplementedError(
                f"Camera {self.name} does not support changing exposure"
            )

        super().update_parameters(exposures=exposures, timeout=timeout)
        exposure = self.exposures[0]
        self.set_exposure(exposure)
        logger.debug(f"{self.name}: exposure set to {exposure}")

    def set_exposure(self, exposure: float):
        ic.IC_SetPropertyAbsoluteValue(
            self._grabber_handle, T("Exposure"), T("Value"), ctypes.c_float(exposure)
        )

    def _start_acquisition(self):
        if not ic.IC_StartLive(self._grabber_handle, 0):
            raise RuntimeError(f"Failed to start live for {self.name}")

        def acquire_pictures():
            for picture_number in range(self.number_pictures_to_acquire):
                self._snap_picture(picture_number, self.timeout)
                image = self._read_picture_from_camera()
                self._pictures[picture_number] = image

        self._acquisition_thread = threading.Thread(target=acquire_pictures)
        self._acquisition_thread.start()

    def _is_acquisition_in_progress(self) -> bool:
        if self._acquisition_thread is None:
            return False
        return self._acquisition_thread.is_alive()

    def _stop_acquisition(self):
        if self._acquisition_thread is not None:
            self._acquisition_thread.join()
            if ic.IC_StopLive(self._grabber_handle) != IC_SUCCESS:
                raise RuntimeError(f"Failed to stop live for {self.name}")

    def _snap_picture(self, picture_number: int, timeout: float) -> None:
        if self.external_trigger:
            timeout = int(timeout * 1e3)
        else:
            timeout = -1
        result = ic.IC_SnapImage(self._grabber_handle, timeout)
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
        return _reformat_image(image, self.format)

    @classmethod
    def get_device_counts(cls) -> int:
        return ic.IC_GetDeviceCount()

    @classmethod
    def get_device_names(cls) -> list[str]:
        return [
            D(ic.IC_GetUniqueNamefromList(i)) for i in range(cls.get_device_counts())
        ]

    def save_state_to_file(self, file):
        if (
            ic.IC_SaveDeviceStateToFile(self._grabber_handle, T(str(file)))
            != IC_SUCCESS
        ):
            raise RuntimeError(f"Failed to save state to file {file}")

    def load_state_from_file(self, file):
        if (
            error := ic.IC_LoadDeviceStateFromFile(self._grabber_handle, T(str(file)))
        ) != IC_SUCCESS:
            raise RuntimeError(f"Failed to load state from file {file}: {error}")

    def reset_properties(self):
        if (error := ic.IC_ResetProperties(self._grabber_handle)) != IC_SUCCESS:
            pass  # not sure why, but the line above returns an error
            # raise RuntimeError(f"Failed to reset properties for {self.name}: {error}")


class ImagingSourceCameraDMK33GR0134(ImagingSourceCamera):
    """ImagingSource camera DMK33GR0134"""

    brightness: int = Field(
        default=0,
        ge=0,
        le=4095,
        description="Brightness of the camera",
        allow_mutation=False,
    )
    contrast: int = Field(
        default=0,
        ge=-10,
        le=30,
        description="Contrast of the camera",
        allow_mutation=False,
    )
    sharpness: int = Field(
        default=0,
        ge=0,
        le=14,
        description="Sharpness of the camera",
        allow_mutation=False,
    )
    gamma: float = Field(
        default=1.0,
        ge=0.01,
        le=5.0,
        description="Gamma of the camera",
        allow_mutation=False,
    )
    gain: float = Field(
        default=0,
        ge=0,
        le=18.04,
        description="Gain of the camera",
        units="dB",
        allow_mutation=False,
    )

    def _setup_properties(self):
        if not ic.IC_SetFormat(self._grabber_handle, _MAP_FORMAT[self.format]):
            raise RuntimeError("Failed to set format")
        if not ic.IC_SetPropertyValue(
            self._grabber_handle, T("Brightness"), T("Value"), self.brightness
        ):
            raise RuntimeError("Failed to set brightness")
        if not ic.IC_SetPropertyValue(
            self._grabber_handle, T("Contrast"), T("Value"), self.contrast
        ):
            raise RuntimeError("Failed to set contrast")
        if not ic.IC_SetPropertyValue(
            self._grabber_handle, T("Sharpness"), T("Value"), self.sharpness
        ):
            raise RuntimeError("Failed to set sharpness")
        if not ic.IC_SetPropertyAbsoluteValue(
            self._grabber_handle, T("Gamma"), T("Value"), ctypes.c_float(self.gamma)
        ):
            raise RuntimeError("Failed to set gamma")
        if not ic.IC_SetPropertySwitch(self._grabber_handle, T("Gain"), T("Auto"), 0):
            raise RuntimeError("Failed to set gain to manual")
        if not ic.IC_SetPropertyAbsoluteValue(
            self._grabber_handle, T("Gain"), T("Value"), ctypes.c_float(self.gain)
        ):
            raise RuntimeError("Failed to set gain")
        if not ic.IC_SetPropertySwitch(
            self._grabber_handle, T("Exposure"), T("Auto"), 0
        ):
            raise RuntimeError("Failed to set exposure to manual")

        if not ic.IC_SetPropertySwitch(
            self._grabber_handle, T("Exposure"), T("Auto"), 0
        ):
            raise RuntimeError("Failed to set exposure to manual")
