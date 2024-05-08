import functools
from collections.abc import Callable
from typing import TypeVar, Optional

from caqtus.utils import serialization
from caqtus.utils.serialization import JSON
from ._protocol import TimeLaneSerializerProtocol
from ..analog_time_lane import AnalogTimeLane
from ..camera_time_lane import CameraTimeLane
from ..digital_time_lane import DigitalTimeLane
from ..timelane import TimeLane

L = TypeVar("L", bound=TimeLane)


class TimeLaneSerializer(TimeLaneSerializerProtocol):
    def __init__(self):
        self._dumper = functools.singledispatch(default_dumper)
        self.loaders: dict[str, Callable[[JSON], TimeLane]] = {}

        self.register_time_lane(
            DigitalTimeLane, dump_digital_lane, load_digital_lane, type_tag="digital"
        )
        self.register_time_lane(
            AnalogTimeLane, dump_analog_lane, load_analog_lane, type_tag="analog"
        )
        self.register_time_lane(
            CameraTimeLane, dump_camera_lane, load_camera_lane, type_tag="camera"
        )

    def register_time_lane(
        self,
        lane_type: type[L],
        dumper: Callable[[L], JSON],
        loader: Callable[[JSON], L],
        type_tag: Optional[str] = None,
    ) -> None:
        if type_tag is None:
            tag = lane_type.__qualname__
        else:
            tag = type_tag
        self._dumper.register(lane_type)(add_tag(dumper, tag))
        self.loaders[tag] = loader

    def dump(self, lane: TimeLane) -> JSON:
        return self._dumper(lane)

    def load(self, data: JSON) -> TimeLane:
        tag = data["type"]
        loader = self.loaders[tag]
        return loader(data)


def add_tag(fun, tag):
    def wrapper(lane):
        content = fun(lane)
        if "type" in content:
            raise ValueError("The content already has a type tag.")
        content["type"] = tag
        return content

    return wrapper


def default_dumper(lane) -> JSON:
    raise NotImplementedError(f"Unsupported type {type(lane)}")


def dump_digital_lane(time_lane: DigitalTimeLane):
    return serialization.converters["json"].unstructure(time_lane, DigitalTimeLane)


def load_digital_lane(content: JSON):
    return serialization.converters["json"].structure(content, DigitalTimeLane)


def dump_analog_lane(time_lane: AnalogTimeLane):
    return serialization.converters["json"].unstructure(time_lane, AnalogTimeLane)


def load_analog_lane(content: JSON):
    return serialization.converters["json"].structure(content, AnalogTimeLane)


def dump_camera_lane(time_lane: CameraTimeLane):
    return serialization.converters["json"].unstructure(time_lane, CameraTimeLane)


def load_camera_lane(content: JSON):
    return serialization.converters["json"].structure(content, CameraTimeLane)
