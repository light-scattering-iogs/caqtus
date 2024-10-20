from caqtus.gui.condetrol.timelanes_editor import TimeLaneModel, AnalogTimeLaneModel
from caqtus.types.expression import Expression
from caqtus.types.timelane import AnalogTimeLane
from caqtus.utils import serialization
from caqtus.utils.serialization import JSON
from ._extension import TimeLaneExtension


def create_analog_lane(number_steps: int) -> AnalogTimeLane:
    return AnalogTimeLane([Expression("...")] * number_steps)


def create_lane_model(lane, lane_name: str) -> TimeLaneModel:
    model = AnalogTimeLaneModel(lane_name)
    model.set_lane(lane)
    return model


def create_lane_delegate(lane, lane_name: str) -> None:
    return None


def dump_analog_lane(time_lane: AnalogTimeLane):
    return serialization.converters["json"].unstructure(time_lane, AnalogTimeLane)


def load_analog_lane(content: JSON):
    return serialization.converters["json"].structure(content, AnalogTimeLane)


analog_time_lane_extension = TimeLaneExtension(
    label="Analog",
    lane_type=AnalogTimeLane,
    dumper=dump_analog_lane,
    loader=load_analog_lane,
    lane_factory=create_analog_lane,
    lane_model_factory=create_lane_model,
    lane_delegate_factory=create_lane_delegate,
    type_tag="analog",
)
