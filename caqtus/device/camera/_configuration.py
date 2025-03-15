from typing import TypeVar

import attrs

from caqtus.shot_compilation import SequenceContext
from caqtus.types.data import ImageType
from caqtus.types.image.roi import RectangularROI
from caqtus.types.timelane import CameraTimeLane
from caqtus.utils.result import Failure, Success, is_failure_type
from ._runtime import Camera
from .. import DeviceName
from ..configuration import DeviceConfiguration
from ..configuration._configuration import DataSchemaError


@attrs.define
class CameraConfiguration[C: Camera](DeviceConfiguration[C]):
    """Contains the necessary information about a camera.

    Attributes:
        roi: The rectangular region of interest to keep for the images taken by the
            camera.
    """

    roi: RectangularROI = attrs.field(
        validator=attrs.validators.instance_of(RectangularROI),
        on_setattr=attrs.setters.validate,
    )

    def get_data_schema(self, name: DeviceName, sequence_context: SequenceContext):
        lane_result = sequence_context.get_lane_by_name(name)
        if is_failure_type(lane_result, KeyError):
            # If the camera lane is not present, it means that the camera is not used
            # in the sequence, and therefore no data is generated.
            return Success({})
        lane = lane_result.content()
        if not isinstance(lane, CameraTimeLane):
            return Failure(
                DataSchemaError(f"Expected a camera time lane for device {name}")
            )
        data_schema = {}
        for picture_label in lane.get_picture_labels():
            data_schema[picture_label] = ImageType(self.roi)
        return Success(data_schema)


CameraConfigurationType = TypeVar("CameraConfigurationType", bound=CameraConfiguration)
