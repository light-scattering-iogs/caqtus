import abc
from typing import TypeVar, TypedDict, Generic

import attrs

from caqtus.session.shot import CameraTimeLane, TakePicture
from caqtus.shot_compilation import SequenceContext, ShotContext
from caqtus.utils.roi import RectangularROI
from ._controller import CameraController
from ._runtime import Camera
from .. import DeviceName
from ..configuration import DeviceConfiguration, DeviceNotUsedException

CameraType = TypeVar("CameraType", bound=Camera)


class CameraUpdateParams(TypedDict):
    timeout: float
    exposures: list[float]


@attrs.define
class CameraConfiguration(
    DeviceConfiguration[CameraType], abc.ABC, Generic[CameraType]
):
    """Contains the necessary information about a camera.

    Attributes:
        roi: The region of interest to keep from the image taken by the camera.
    """

    roi: RectangularROI = attrs.field(
        validator=attrs.validators.instance_of(RectangularROI),
        on_setattr=attrs.setters.validate,
    )

    @abc.abstractmethod
    def get_device_initialization_method(
        self, device_name: DeviceName, sequence_context: SequenceContext
    ):
        try:
            sequence_context.get_lane(device_name)
        except KeyError:
            raise DeviceNotUsedException(device_name)
        return (
            super()
            .get_device_initialization_method(device_name, sequence_context)
            .with_extra_parameters(roi=self.roi, external_trigger=True, timeout=1.0)
        )

    def get_controller_type(self):
        return CameraController

    @abc.abstractmethod
    def compile_device_shot_parameters(
        self,
        device_name: DeviceName,
        shot_context: ShotContext,
    ) -> CameraUpdateParams:
        lane = shot_context.get_lane(device_name)
        if not isinstance(lane, CameraTimeLane):
            raise TypeError(f"Expected a camera lane for device {device_name}")
        step_durations = shot_context.get_step_durations()
        exposures = []
        for value, (start, stop) in zip(lane.values(), lane.bounds()):
            if isinstance(value, TakePicture):
                exposure = sum(step_durations[start:stop])
                exposures.append(exposure)
        return CameraUpdateParams(
            # Add a bit of extra time to the timeout, in case the shot takes a bit of
            # time to actually start.
            timeout=shot_context.get_shot_duration() + 1,
            exposures=exposures,
        )
