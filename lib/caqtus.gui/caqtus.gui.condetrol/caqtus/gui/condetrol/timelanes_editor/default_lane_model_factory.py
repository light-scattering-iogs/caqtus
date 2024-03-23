from caqtus.session.shot import (
    TimeLane,
    DigitalTimeLane,
    AnalogTimeLane,
    CameraTimeLane,
)

from .analog_lane_model import AnalogTimeLaneModel
from .camera_lane_model import CameraTimeLaneModel
from .digital_lane_model import DigitalTimeLaneModel
from .model import TimeLaneModel


def default_lane_model_factory(lane: TimeLane) -> type[TimeLaneModel]:
    match lane:
        case DigitalTimeLane():
            return DigitalTimeLaneModel
        case AnalogTimeLane():
            return AnalogTimeLaneModel
        case CameraTimeLane():
            return CameraTimeLaneModel
        case _:
            raise NotImplementedError
