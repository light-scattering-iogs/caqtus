from core.session.shot import TimeLane, DigitalTimeLane, AnalogTimeLane

from .analog_lane_model import AnalogTimeLaneModel
from .digital_lane_model import DigitalTimeLaneModel
from .model import TimeLaneModel


def default_lane_model_factory(lane: TimeLane) -> type[TimeLaneModel]:
    match lane:
        case DigitalTimeLane():
            return DigitalTimeLaneModel
        case AnalogTimeLane():
            return AnalogTimeLaneModel
        case _:
            raise NotImplementedError
