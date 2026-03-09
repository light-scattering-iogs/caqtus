from caqtus.types.timelane import DigitalTimeLane
from caqtus.utils import serialization
from caqtus.utils.serialization import JSON
from ._extension import TimeLaneExtension
from ...gui.condetrol.timelanes_editor import TimeLaneModel
from ...gui.condetrol.timelanes_editor.digital_lane_editor import (
    DigitalTimeLaneModel,
    DigitalTimeLaneDelegate,
)


def create_digital_lane(number_steps: int) -> DigitalTimeLane:
    return DigitalTimeLane([False] * number_steps)


def create_lane_model(lane, lane_name: str) -> TimeLaneModel:
    model = DigitalTimeLaneModel(lane_name)
    model.set_lane(lane)
    return model


def create_lane_delegate(lane, lane_name: str) -> DigitalTimeLaneDelegate:
    return DigitalTimeLaneDelegate()


def dump_digital_lane(time_lane: DigitalTimeLane):
    return serialization.converters["json"].unstructure(time_lane, DigitalTimeLane)


def load_digital_lane(content: JSON):
    return serialization.converters["json"].structure(content, DigitalTimeLane)


digital_time_lane_extension = TimeLaneExtension(
    label="Digital",
    lane_type=DigitalTimeLane,
    dumper=dump_digital_lane,
    loader=load_digital_lane,
    lane_factory=create_digital_lane,
    lane_model_factory=create_lane_model,
    lane_delegate_factory=create_lane_delegate,
    type_tag="digital",
)
