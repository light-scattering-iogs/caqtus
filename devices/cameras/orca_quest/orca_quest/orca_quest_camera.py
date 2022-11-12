import atexit
import logging
import time
from typing import ClassVar, Optional, Final

import numpy
from pydantic import Field

from camera import CCamera

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

try:
    from .dcam import Dcamapi, Dcam, DCAM_IDSTR
    from .dcamapi4 import DCAM_IDPROP, DCAMPROP
except FileNotFoundError:
    logger.warning("Could not load DCAM-API")


class OrcaQuestCamera(CCamera):
    camera_number: int = Field(
        description="The camera number used to identify the specific camera.",
        allow_mutation=False,
    )

    sensor_width: Final = 4096
    sensor_height: Final = 2304

    _pictures: list[Optional[numpy.ndarray]]
    _camera: Dcam

    def start(self) -> None:
        super().start()
        self._pictures = [None] * self.number_pictures_to_acquire
        if not Dcamapi.init():
            raise RuntimeError(
                f"Failed to initialize DCAM-API: {str(Dcamapi.lasterr())}"
            )
        else:
            logger.info(f"{self.name}: DCAM-API initialized")
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

        # TODO: fix subarray properties being ignored
        properties = {
            # DCAM_IDPROP.SUBARRAYMODE: True,
            # DCAM_IDPROP.SUBARRAYHPOS: self.roi.x,
            # DCAM_IDPROP.SUBARRAYHSIZE: self.roi.width,
            # DCAM_IDPROP.SUBARRAYVPOS: self.roi.y,
            # DCAM_IDPROP.SUBARRAYVSIZE: self.roi.height,
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
                    f"Failed to set property {str(property_id)} to {str(property_value)} for {self.name}: "
                    f"{str(self._camera.lasterr())}"
                )

        if not self._camera.buf_alloc(1):
            raise RuntimeError(
                f"Failed to allocate buffer for images: {str(self._camera.lasterr())}"
            )

    def shutdown(self):
        if self._camera.buf_release():
            logger.info(f"{self.name}: DCAM buffer successfully released")
        else:
            logger.warning(
                f"{self.name}: an error occurred while releasing DCAM buffer: {str(self._camera.lasterr())}"
            )

        if self._camera.is_opened():
            if self._camera.dev_close():
                logger.info(f"{self.name}: camera successfully released")
            else:
                logger.warning(
                    f"{self.name}: an error occurred while closing the camera: {str(self._camera.lasterr())}"
                )
        if Dcamapi.uninit():
            logger.info(f"{self.name}: DCAM-API successfully released")

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
            logger.debug(camera.lasterr())
        return result

    @classmethod
    def _initialize_dcam_api(cls):
        if not (result := cls._dcam_api_initialized):
            result = Dcamapi.init()
            if result:
                cls._dcam_api_initialized = True
                atexit.register(Dcamapi.uninit)
            else:
                raise RuntimeError(
                    f"Failed to initialize DCAM-API: {str(Dcamapi.lasterr())}"
                )
        return result

    _dcam_api_initialized: ClassVar[bool] = False

    def _acquire_picture(
        self, picture_number: int, new_exposure: float, timeout: float
    ):
        if (exposure := self._camera.prop_getvalue(DCAM_IDPROP.EXPOSURETIME)) is False:
            raise RuntimeError(
                f"Can't access exposure property of {self.name}: {str(self._camera.lasterr())}"
            )
        else:
            if exposure != new_exposure:
                if not self._camera.prop_setvalue(
                    DCAM_IDPROP.EXPOSURETIME, new_exposure
                ):
                    raise RuntimeError(
                        f"Can't set exposure of {self.name} to {new_exposure}: {str(self._camera.lasterr())}"
                    )
        if self._camera.cap_snapshot() is not False:
            start_acquire = time.time()
            while True:
                if self._camera.wait_capevent_frameready(1):
                    data = self._camera.buf_getlastframedata()
                    roi = self.roi
                    self._pictures[picture_number] = data.T[
                        roi.x : roi.x + roi.width, roi.y : roi.y + roi.height
                    ]
                    self._picture_acquired(picture_number)
                    logger.info(
                        f"{self.name}: picture '{self.picture_names[picture_number]}' acquired after "
                        f"{(time.time() - start_acquire) * 1e3:.0f} ms"
                    )
                    break

                error = self._camera.lasterr()
                if error.is_timeout():
                    if time.time() - start_acquire > self.timeout:
                        raise TimeoutError(
                            f"{self.name} timed out before receiving a trigger"
                        )
                    pass
                else:
                    raise RuntimeError(
                        f"An error occurred while acquiring an image on {self.name}: {str(error)}"
                    )
        else:
            raise RuntimeError(
                f"Failed to start capture for {self.name}: {str(self._camera.lasterr())}"
            )

    def _read_picture(self, picture_number: int) -> numpy.ndarray:
        super()._read_picture(picture_number)
        return self._pictures[picture_number]
