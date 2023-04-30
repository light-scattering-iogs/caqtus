import atexit
import logging
import time
from concurrent.futures import ThreadPoolExecutor, Future
from copy import copy
from typing import Optional

import numpy
import numpy as np
from pydantic import Field

from camera.runtime import CCamera, CameraTimeoutError
from .dcam import Dcamapi, Dcam, DCAM_IDSTR
from .dcamapi4 import DCAM_IDPROP, DCAMPROP

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

if Dcamapi.init():
    atexit.register(Dcamapi.uninit)
else:
    # If this error occurs, check that the dcam-api from hamamatsu is installed
    # https://dcam-api.com/
    raise ImportError(f"Failed to initialize DCAM-API: {Dcamapi.lasterr()}")


class OrcaQuestCamera(CCamera):
    # only some specific roi values are allowed for this camera !
    camera_number: int = Field(
        description="The camera number used to identify the specific camera.",
        allow_mutation=False,
    )

    sensor_width = 4096
    sensor_height = 2304

    _pictures: list[Optional[numpy.ndarray]]
    _camera: "Dcam"
    # _acquisition_thread: Optional[threading.Thread] = None
    _current_exposure: Optional[float] = None
    _thread_pool_executor: ThreadPoolExecutor
    _future: Optional[Future] = None

    @classmethod
    def exposed_remote_methods(cls) -> tuple[str, ...]:
        return super().exposed_remote_methods() + ("list_properties",)

    def initialize(self) -> None:
        super().initialize()
        self._thread_pool_executor = ThreadPoolExecutor(max_workers=1)
        self._pictures = [None] * self.number_pictures_to_acquire

        if self.camera_number < Dcamapi.get_devicecount():
            self._camera = Dcam(self.camera_number)
        else:
            raise RuntimeError(f"Could not find camera {str(self.camera_number)}")

        if not self._camera.dev_open():
            raise RuntimeError(
                f"Failed to open camera {self.name}: {str(self._camera.lasterr())}"
            )
        else:
            logger.info(f"{self.name}: successfully opened camera {self.camera_number}")

        if not self._camera.prop_setvalue(DCAM_IDPROP.SUBARRAYMODE, DCAMPROP.MODE.OFF):
            raise RuntimeError(
                f"can't set subarray mode off: {str(self._camera.lasterr())}"
            )

        properties = {
            DCAM_IDPROP.SUBARRAYHPOS: self.roi.x,
            DCAM_IDPROP.SUBARRAYHSIZE: self.roi.width,
            DCAM_IDPROP.SUBARRAYVPOS: self.roi.y,
            DCAM_IDPROP.SUBARRAYVSIZE: self.roi.height,
            DCAM_IDPROP.SENSORMODE: DCAMPROP.SENSORMODE.AREA,
            DCAM_IDPROP.TRIGGER_GLOBALEXPOSURE: DCAMPROP.TRIGGER_GLOBALEXPOSURE.GLOBALRESET,
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
                    f" {str(self._camera.lasterr())}"
                )

            self._camera.lasterr()

        if not self._camera.prop_setvalue(DCAM_IDPROP.SUBARRAYMODE, DCAMPROP.MODE.ON):
            raise RuntimeError(
                f"can't set subarray mode on: {str(self._camera.lasterr())}"
            )

        if not self._camera.buf_alloc(self.number_pictures_to_acquire):
            raise RuntimeError(
                f"Failed to allocate buffer for images: {str(self._camera.lasterr())}"
            )
        logger.debug(f"{self.name}: buffer successfully allocated")

    def shutdown(self):
        try:
            if self._camera.buf_release():
                logger.info(f"{self.name}: DCAM buffer successfully released")
            else:
                logger.warning(
                    f"{self.name}: an error occurred while releasing DCAM buffer:"
                    f" {str(self._camera.lasterr())}"
                )

            if self._camera.is_opened():
                if self._camera.dev_close():
                    logger.info(f"{self.name}: camera successfully released")
                else:
                    logger.warning(
                        f"{self.name}: an error occurred while closing the camera:"
                        f" {str(self._camera.lasterr())}"
                    )

        finally:
            super().shutdown()

    def list_properties(self) -> list:
        result = []
        property_id = self._camera.prop_getnextid(0)
        while property_id:
            property_name = self._camera.prop_getname(property_id)
            if property_name:
                result.append((property_id, property_name))
            property_id = self._camera.prop_getnextid(property_id)
        return result

    def _start_acquisition(self, number_pictures: int):
        exposures = copy(self.exposures)
        new_exposure = exposures[0]
        if self._current_exposure != new_exposure:
            if not self._camera.prop_setvalue(DCAM_IDPROP.EXPOSURETIME, new_exposure):
                raise RuntimeError(
                    f"Can't set exposure of {self.name} to {new_exposure}:"
                    f" {str(self._camera.lasterr())}"
                )
            self._current_exposure = new_exposure
        if not self._camera.cap_start(bSequence=True):
            raise RuntimeError(
                f"Can't start acquisition on {self.name}: {str(self._camera.lasterr())}"
            )

        def acquire_pictures():
            try:
                for picture_number, exposure in enumerate(exposures):
                    if self._current_exposure != exposure:
                        if not self._camera.prop_setvalue(
                            DCAM_IDPROP.EXPOSURETIME, exposure
                        ):
                            raise RuntimeError(
                                f"Can't set exposure of {self.name} to {exposure}:"
                                f" {str(self._camera.lasterr())}"
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
                        f"{self.name} timed out after {timeout*1e3:.0f} ms before"
                        " receiving a trigger"
                    )
                continue
            else:
                raise RuntimeError(
                    f"An error occurred while acquiring an image on {self.name}:"
                    f" {str(error)}"
                )

    def _stop_acquisition(self):
        if self._future is not None:
            self._future.result()

    def _is_acquisition_in_progress(self) -> bool:
        if self._future is None:
            return False
        return not self._future.done()

    @classmethod
    def list_camera_infos(cls) -> list[dict[str]]:
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
