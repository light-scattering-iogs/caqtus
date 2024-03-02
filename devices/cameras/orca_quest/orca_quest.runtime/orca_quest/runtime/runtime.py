import atexit
import logging
import numpy as np
import time
from attrs import define, field
from attrs.setters import frozen
from attrs.validators import instance_of
from concurrent.futures import ThreadPoolExecutor, Future
from copy import copy
from core.device.camera.runtime import Camera, CameraTimeoutError
from typing import Optional, Any, ClassVar

from util import log_exception
from .dcam import Dcamapi, Dcam, DCAM_IDSTR
from .dcamapi4 import DCAM_IDPROP, DCAMPROP, DCAMERR

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


@define(slots=False)
class OrcaQuestCamera(Camera):
    """

    Beware that not all roi values are allowed for this camera. In doubt, try to check if the ROI is valid using the
    HCImageLive software.

    Fields:
        camera_number: The camera number used to identify the specific camera.
    """

    sensor_width: ClassVar[int] = 4096
    sensor_height: ClassVar[int] = 2304

    camera_number: int = field(validator=instance_of(int), on_setattr=frozen)

    _pictures: list[Optional[np.ndarray]] = field(init=False)
    _camera: Dcam = field(init=False)
    _thread_pool_executor: ThreadPoolExecutor = field(init=False)
    _current_exposure: Optional[float] = field(default=None, init=False)
    _future: Optional[Future] = field(default=None, init=False)

    @classmethod
    def exposed_remote_methods(cls) -> tuple[str, ...]:
        return super().exposed_remote_methods() + ("list_properties",)

    def _read_last_error(self) -> str:
        return DCAMERR(self._camera.lasterr()).name

    @log_exception(logger)
    def initialize(self) -> None:
        super().initialize()
        if Dcamapi.init():
            self._add_closing_callback(Dcamapi.uninit)
        else:
            # If this error occurs, check that the dcam-api from hamamatsu is installed
            # https://dcam-api.com/
            raise ImportError(
                f"Failed to initialize DCAM-API: {Dcamapi.lasterr().name}"
            )
        self._thread_pool_executor = ThreadPoolExecutor(max_workers=1)
        self._pictures = [None] * self.number_pictures_to_acquire

        if self.camera_number < Dcamapi.get_devicecount():
            self._camera = Dcam(self.camera_number)
        else:
            raise RuntimeError(f"Could not find camera {str(self.camera_number)}")

        if not self._camera.dev_open():
            raise RuntimeError(
                f"Failed to open camera {self.name}: {self._read_last_error()}"
            )
        self._add_closing_callback(self._camera.dev_close)
        logger.info(f"{self.name}: successfully opened camera {self.camera_number}")

        if not self._camera.prop_setvalue(DCAM_IDPROP.SUBARRAYMODE, DCAMPROP.MODE.OFF):
            raise RuntimeError(
                f"can't set subarray mode off: {self._read_last_error()}"
            )

        properties = {
            DCAM_IDPROP.SUBARRAYHPOS: self.roi.x,
            DCAM_IDPROP.SUBARRAYHSIZE: self.roi.width,
            DCAM_IDPROP.SUBARRAYVPOS: self.roi.y,
            DCAM_IDPROP.SUBARRAYVSIZE: self.roi.height,
            DCAM_IDPROP.SENSORMODE: DCAMPROP.SENSORMODE.AREA,
            DCAM_IDPROP.TRIGGER_GLOBALEXPOSURE: DCAMPROP.TRIGGER_GLOBALEXPOSURE.DELAYED,
        }

        if self.external_trigger:
            properties[DCAM_IDPROP.TRIGGERSOURCE] = DCAMPROP.TRIGGERSOURCE.EXTERNAL
            properties[DCAM_IDPROP.TRIGGERACTIVE] = DCAMPROP.TRIGGERACTIVE.EDGE
            properties[DCAM_IDPROP.TRIGGERPOLARITY] = DCAMPROP.TRIGGERPOLARITY.POSITIVE
        else:
            properties[DCAM_IDPROP.TRIGGERSOURCE] = DCAMPROP.TRIGGERSOURCE.INTERNAL

        for property_id, property_value in properties.items():
            if not self._camera.prop_setvalue(property_id, property_value):
                raise RuntimeError(
                    f"Failed to set property {str(property_id)} to"
                    f" {str(property_value)} for {self.name}:"
                    f" {self._read_last_error()}"
                )

            self._read_last_error()

        if not self._camera.prop_setvalue(DCAM_IDPROP.SUBARRAYMODE, DCAMPROP.MODE.ON):
            raise RuntimeError(f"can't set subarray mode on: {self._read_last_error()}")

        # We can't allocate 0 pictures in the buffer, so we allocate at least 1
        number_picture_in_buffer = self.number_pictures_to_acquire if self.number_pictures_to_acquire > 0 else 1
        if not self._camera.buf_alloc(number_picture_in_buffer):
            raise RuntimeError(
                f"Failed to allocate buffer for images: {self._read_last_error()}"
            )
        self._add_closing_callback(self._camera.buf_release)
        logger.debug(f"{self.name}: buffer successfully allocated")

    def list_properties(self) -> list:
        result = []
        property_id = self._camera.prop_getnextid(0)
        while property_id:
            property_name = self._camera.prop_getname(property_id)
            if property_name:
                result.append((property_id, property_name))
            property_id = self._camera.prop_getnextid(property_id)
        return result

    @log_exception(logger)
    def _start_acquisition(self, number_pictures: int):
        exposures = copy(self.exposures)
        new_exposure = exposures[0]
        if self._current_exposure != new_exposure:
            if not self._camera.prop_setvalue(DCAM_IDPROP.EXPOSURETIME, new_exposure):
                raise RuntimeError(
                    f"Can't set exposure of {self.name} to {new_exposure}:"
                    f" {self._read_last_error()}"
                )
            self._current_exposure = new_exposure
        if not self._camera.cap_start(bSequence=True):
            raise RuntimeError(
                f"Can't start acquisition on {self.name}: {self._read_last_error()}"
            )

        @log_exception(logger)
        def acquire_pictures():
            try:
                for picture_number, exposure in enumerate(exposures):
                    if self._current_exposure != exposure:
                        if not self._camera.prop_setvalue(
                            DCAM_IDPROP.EXPOSURETIME, exposure
                        ):
                            raise RuntimeError(
                                f"Can't set exposure of {self.name} to {exposure}:"
                                f" {self._read_last_error()}"
                            )
                        self._current_exposure = exposure
                    self._acquire_picture(picture_number, self.timeout)
            finally:
                self._camera.cap_stop()

        self._future = self._thread_pool_executor.submit(acquire_pictures)

    def _acquire_picture(self, picture_number: int, timeout: float):
        start_acquire = time.time()
        while True:
            if self._camera.wait_capevent_frameready(1):
                data = self._camera.buf_getlastframedata()
                self._pictures[picture_number] = data.T
                logger.info(
                    f"{self.name}: picture '{self.picture_names[picture_number]}'"
                    f" acquired after {(time.time() - start_acquire) * 1e3:.0f} ms"
                )
                break

            error = self._camera.lasterr()
            if error.is_timeout():
                if time.time() - start_acquire > self.timeout:
                    for picture_number in range(picture_number, len(self.exposures)):
                        self._pictures[picture_number] = np.full(
                            (self.roi.width, self.roi.height), np.nan
                        )
                    raise CameraTimeoutError(
                        f"{self.name} timed out after {timeout*1e3:.0f} ms without"
                        f" receiving a trigger, only received {picture_number} out of {len(self.exposures)} pictures"
                    )
                continue
            else:
                raise RuntimeError(
                    f"An error occurred while acquiring an image on {self.name}:"
                    f" {str(error)}"
                )

    @log_exception(logger)
    def _stop_acquisition(self):
        if self._future is not None:
            self._future.result()

    @log_exception(logger)
    def _is_acquisition_in_progress(self) -> bool:
        if self._future is None:
            return False
        return not self._future.done()

    @classmethod
    def list_camera_infos(cls) -> list[dict[str, Any]]:
        result = []
        for camera_index in range(Dcamapi.get_devicecount()):
            infos = {}
            camera = Dcam(camera_index)
            infos["id"] = camera.dev_getstring(DCAM_IDSTR.CAMERAID)
            infos["model"] = camera.dev_getstring(DCAM_IDSTR.MODEL)
            infos["camera version"] = camera.dev_getstring(DCAM_IDSTR.CAMERAVERSION)
            infos["driver version"] = camera.dev_getstring(DCAM_IDSTR.DRIVERVERSION)
            result.append(infos)
        return result
