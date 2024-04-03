import logging
import time
from typing import Any, ClassVar, Optional

from attrs import define, field
from attrs.setters import frozen
from attrs.validators import instance_of
from caqtus.device import RuntimeDevice
from caqtus.device.camera import Camera, CameraTimeoutError
from caqtus.types.image import Image
from caqtus.utils import log_exception

from .dcam import Dcamapi, Dcam, DCAM_IDSTR
from .dcamapi4 import DCAM_IDPROP, DCAMPROP, DCAMERR

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


@define(slots=False)
class OrcaQuestCamera(Camera, RuntimeDevice):
    """

    Beware that not all roi values are allowed for this camera.
    In doubt, try to check if the ROI is valid using the HCImageLive software.

    Fields:
        camera_number: The camera number used to identify the specific camera.
    """

    sensor_width: ClassVar[int] = 4096
    sensor_height: ClassVar[int] = 2304

    camera_number: int = field(validator=instance_of(int), on_setattr=frozen)

    _camera: Dcam = field(init=False)
    _buffer_number_pictures: Optional[int] = field(init=False, default=None)

    def _read_last_error(self) -> str:
        return DCAMERR(self._camera.lasterr()).name

    def update_parameters(self, timeout: float) -> None:
        self.timeout = timeout

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
            # The Camera is set to acquire images when the trigger is high.
            # This allows changing the exposure by changing the trigger duration and
            # without having to communicate with the camera.
            # With this it is possible to change the exposure of two very close pictures.
            # However, the trigger received by the camera must be clean.
            # If it bounces, the acquisition will be messed up.
            # To prevent bouncing, it might be necessary to add a 50 Ohm resistor before the camera trigger input.
            properties[DCAM_IDPROP.TRIGGERSOURCE] = DCAMPROP.TRIGGERSOURCE.EXTERNAL
            properties[DCAM_IDPROP.TRIGGERACTIVE] = DCAMPROP.TRIGGERACTIVE.LEVEL
            properties[DCAM_IDPROP.TRIGGERPOLARITY] = DCAMPROP.TRIGGERPOLARITY.POSITIVE
        else:
            raise NotImplementedError("Only external trigger is supported")
            # Need to handle different exposures when using internal trigger, so it is not implemented yet.
            # properties[DCAM_IDPROP.TRIGGERSOURCE] = DCAMPROP.TRIGGERSOURCE.INTERNAL

        for property_id, property_value in properties.items():
            if not self._camera.prop_setvalue(property_id, property_value):
                raise RuntimeError(
                    f"Failed to set property {str(property_id)} to"
                    f" {str(property_value)} for {self.name}:"
                    f" {self._read_last_error()}"
                )

        if not self._camera.prop_setvalue(DCAM_IDPROP.SUBARRAYMODE, DCAMPROP.MODE.ON):
            raise RuntimeError(f"can't set subarray mode on: {self._read_last_error()}")

        if not self._camera.buf_alloc(10):
            raise RuntimeError(
                f"Failed to allocate buffer for images: {self._read_last_error()}"
            )
        self._add_closing_callback(self._camera.buf_release)

    def _start_acquisition(self, exposures: list[float]) -> None:
        if not self._camera.cap_start(bSequence=True):
            raise RuntimeError(
                f"Can't start acquisition for {self}: {self._read_last_error()}"
            )

    def _read_image(self, exposure: float) -> Image:
        # Should change the exposure time if not in gated mode
        # self._camera.prop_setvalue(DCAM_IDPROP.EXPOSURETIME, new_exposure)
        return self._acquire_picture(self.timeout)

    def _stop_acquisition(self) -> None:
        if not self._camera.cap_stop():
            raise RuntimeError(
                f"Failed to stop acquisition for {self}: {self._read_last_error()}"
            )

    def list_properties(self) -> list:
        result = []
        property_id = self._camera.prop_getnextid(0)
        while property_id:
            property_name = self._camera.prop_getname(property_id)
            if property_name:
                result.append((property_id, property_name))
            property_id = self._camera.prop_getnextid(property_id)
        return result

    def _acquire_picture(self, timeout: float) -> Image:
        start_acquire = time.time()
        while True:
            if self._camera.wait_capevent_frameready(1):
                data = self._camera.buf_getlastframedata()
                return data.T
            error = self._camera.lasterr()
            if error.is_timeout():
                if time.time() - start_acquire > self.timeout:
                    raise CameraTimeoutError(
                        f"{self.name} timed out after {timeout*1e3:.0f} ms without"
                        f" receiving a trigger"
                    )
                continue
            else:
                raise RuntimeError(
                    f"An error occurred during acquisition for {self}: {error}"
                )

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
