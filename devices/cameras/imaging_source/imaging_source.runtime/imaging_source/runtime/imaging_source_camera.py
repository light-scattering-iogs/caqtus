"""This module provide a class to use an Imaging Source camera.

Note that to import this package, the library tisgrabber_x64.dll must be installed.
The library can be downloaded from the Imaging Source website.
In the download page (https://www.theimagingsource.com/en-us/support/download/),
section SDK, install the IC Imaging Control C Library if you are using Windows.
Untested on other platforms.
"""

import ctypes
import logging
import os
import pathlib
import threading
from abc import ABC, abstractmethod
from typing import Literal

import numpy
from attrs import define, field
from attrs.setters import frozen
from attrs.validators import instance_of, in_, ge, le
from core.device.camera import Camera, CameraTimeoutError

from .tisgrabber import declareFunctions, D, T, HGRABBER, IC_SUCCESS

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Edit this path if the library is installed in a different location
tisgrabber_path = (
    os.path.expanduser("~")
    + r"\Documents\The Imaging Source Europe GmbH\TIS Grabber DLL\bin\x64\tisgrabber_x64.dll"
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


@define(slots=False)
class ImagingSourceCamera(Camera, ABC):
    """

    Fields:
        camera_name: The name of the camera
    """

    camera_name: str = field(validator=instance_of(str), on_setattr=frozen)
    format: Literal["Y16", "Y800"] = field(
        default="Y16", validator=in_(["Y16", "Y800"]), on_setattr=frozen
    )

    _grabber_handle: ctypes.POINTER(HGRABBER) = field(init=False)
    _acquisition_thread: threading.Thread = field(init=False)
    _temp_dir: pathlib.Path = field(init=False)
    _settings_file: pathlib.Path = field(init=False)

    def initialize(self):
        super().initialize()
        self._grabber_handle = ic.IC_CreateGrabber()
        self._add_closing_callback(ic.IC_ReleaseGrabber, self._grabber_handle)

        ic.IC_OpenDevByUniqueName(self._grabber_handle, T(self.camera_name))
        if not ic.IC_IsDevValid(self._grabber_handle):
            raise RuntimeError(f"{self.name}: camera {self.camera_name} not found")
        self._add_closing_callback(
            ic.IC_CloseDev, self._grabber_handle
        )  # TODO: check if this is necessary
        self._add_closing_callback(ic.IC_StopLive, self._grabber_handle)

        logger.info(f"{self.name}: camera {self.camera_name} found")

        self._setup_properties()
        self._setup_trigger()

        self.update_parameters(exposures=self.exposures, timeout=self.timeout)

    @abstractmethod
    def _setup_properties(self):
        """Set up the properties of the camera after their reinitialization"""
        ...

    def _setup_trigger(self):
        if (
            ic.IC_EnableTrigger(self._grabber_handle, int(self.external_trigger))
            != IC_SUCCESS
        ):
            raise RuntimeError(f"{self.name}: failed to set trigger mode")
        logger.debug(f"{self.name}: trigger mode set to {self.external_trigger}")

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

    def _start_acquisition(self, number_pictures: int):
        if not ic.IC_StartLive(self._grabber_handle, 0):
            raise RuntimeError(f"Failed to start live for {self.name}")

        def acquire_pictures():
            for picture_number in range(number_pictures):
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
        logger.debug(f"Acquiring picture {picture_number} with timeout {timeout}...")
        if self.external_trigger:
            timeout = int(timeout * 1e3)
        else:
            timeout = -1
        result = ic.IC_SnapImage(self._grabber_handle, timeout)
        if result == IC_SUCCESS:
            logger.info(f"Picture {picture_number} acquired")
        else:
            raise CameraTimeoutError(f"Failed to acquire picture, error code: {result}")

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
        formatted_image = _reformat_image(image, self.format).transpose()
        roi = (
            slice(self.roi.x, self.roi.x + self.roi.width),
            slice(self.roi.y, self.roi.y + self.roi.height),
        )
        return formatted_image[roi]

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


@define(slots=False)
class ImagingSourceCameraDMK33GR0134(ImagingSourceCamera):
    """ImagingSource camera DMK33GR0134

    Fields:
        brightness: Brightness of the camera
        contrast: Contrast of the camera
        sharpness: Sharpness of the camera
        gamma: Gamma of the camera
        gain: Gain of the camera, in dB
    """

    brightness: int = field(
        default=0,
        validator=(instance_of(int), in_(range(0, 4096))),
        on_setattr=frozen,
    )
    contrast: int = field(
        default=0,
        validator=(instance_of(int), in_(range(-10, 31))),
        on_setattr=frozen,
    )
    sharpness: int = field(
        default=0,
        validator=(instance_of(int), in_(range(0, 15))),
        on_setattr=frozen,
    )
    gamma: float = field(
        default=1.0,
        validator=(instance_of(float), ge(0.01), le(5.0)),
        on_setattr=frozen,
    )
    gain: float = field(
        default=0,
        validator=(instance_of(float), ge(0), le(18.04)),
        on_setattr=frozen,
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
