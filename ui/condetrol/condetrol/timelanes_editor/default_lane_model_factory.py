from core.session.shot import TimeLane, DigitalTimeLane
from .digital_lane_model import DigitalTimeLaneModel
from .model import TimeLaneModel


def default_lane_model_factory(lane: TimeLane) -> type[TimeLaneModel]:
    match lane:
        case DigitalTimeLane():
            return DigitalTimeLaneModel
        case _:
            raise NotImplementedError
