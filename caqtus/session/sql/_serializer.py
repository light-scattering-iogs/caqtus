from __future__ import annotations

import functools
from collections.abc import Callable, Mapping
from typing import Generic, TypeVar

import attrs

from caqtus.device import DeviceConfiguration
from caqtus.session.shot.timelane import AnalogTimeLane
from caqtus.utils import serialization
from caqtus.utils.serialization import JSON
from ..sequence.iteration_configuration import (
    IterationConfiguration,
    StepsConfiguration,
)
from ..shot import TimeLane, DigitalTimeLane, CameraTimeLane

T = TypeVar("T", bound=DeviceConfiguration)


@attrs.define
class Serializer:
    """Serialize and deserialize user objects."""

    sequence_serializer: SequenceSerializer
    device_configuration_serializers: Mapping[str, DeviceConfigurationSerializer]

    def dump_device_configuration(
        self, config: DeviceConfiguration
    ) -> tuple[str, serialization.JSON]:
        type_name = type(config).__qualname__
        serializer = self.device_configuration_serializers[type_name]
        content = serializer.dumper(config)
        return type_name, content

    def load_device_configuration(
        self, tag: str, content: serialization.JSON
    ) -> DeviceConfiguration:
        serializer = self.device_configuration_serializers[tag]
        device_config = serializer.loader(content)
        return device_config

    def construct_sequence_iteration(
        self, content: serialization.JSON
    ) -> IterationConfiguration:
        return self.sequence_serializer.iteration_constructor(content)

    def dump_sequence_iteration(
        self, iteration: IterationConfiguration
    ) -> serialization.JSON:
        return self.sequence_serializer.iteration_serializer(iteration)

    def dump_time_lane(self, lane: TimeLane) -> serialization.JSON:
        return self.sequence_serializer.time_lane_serializer(lane)

    def construct_time_lane(self, content: serialization.JSON) -> TimeLane:
        return self.sequence_serializer.time_lane_constructor(content)


@attrs.define
class DeviceConfigurationSerializer(Generic[T]):
    """Indicates how to serialize and deserialize device configurations."""

    dumper: Callable[[T], JSON]
    loader: Callable[[JSON], T]


@attrs.define
class SequenceSerializer:
    """Indicates how to serialize and deserialize sequence configurations."""

    iteration_serializer: Callable[[IterationConfiguration], serialization.JSON]
    iteration_constructor: Callable[[serialization.JSON], IterationConfiguration]
    time_lane_serializer: Callable[[TimeLane], serialization.JSON]
    time_lane_constructor: Callable[[serialization.JSON], TimeLane]


@functools.singledispatch
def default_iteration_configuration_serializer(
    iteration_configuration: IterationConfiguration,
) -> serialization.JSON:
    raise TypeError(
        f"Cannot serialize iteration configuration of type "
        f"{type(iteration_configuration)}"
    )


@default_iteration_configuration_serializer.register
def _(
    iteration_configuration: StepsConfiguration,
):
    content = serialization.converters["json"].unstructure(iteration_configuration)
    content["type"] = "steps"
    return content


def default_iteration_configuration_constructor(
    iteration_content: serialization.JSON,
) -> IterationConfiguration:
    iteration_type = iteration_content.pop("type")
    if iteration_type == "steps":
        return serialization.converters["json"].structure(
            iteration_content, StepsConfiguration
        )
    else:
        raise ValueError(f"Unknown iteration type {iteration_type}")


@functools.singledispatch
def default_time_lane_serializer(time_lane: TimeLane) -> serialization.JSON:
    error = TypeError(f"Cannot serialize time lane of type {type(time_lane)}")

    error.add_note(
        f"{default_time_lane_serializer} doesn't support saving this lane type."
    )
    error.add_note(
        "You need to provide a custom lane serializer to the experiment session maker."
    )
    raise error


@default_time_lane_serializer.register
def _(time_lane: DigitalTimeLane):
    content = serialization.converters["json"].unstructure(time_lane, DigitalTimeLane)
    content["type"] = "digital"
    return content


@default_time_lane_serializer.register
def _(time_lane: AnalogTimeLane):
    content = serialization.converters["json"].unstructure(time_lane, AnalogTimeLane)
    content["type"] = "analog"
    return content


@default_time_lane_serializer.register
def _(time_lane: CameraTimeLane):
    content = serialization.converters["json"].unstructure(time_lane, CameraTimeLane)
    content["type"] = "camera"
    return content


def default_time_lane_constructor(
    time_lane_content: serialization.JSON,
) -> TimeLane:
    time_lane_type = time_lane_content.pop("type")
    if time_lane_type == "digital":
        return serialization.converters["json"].structure(
            time_lane_content, DigitalTimeLane
        )
    elif time_lane_type == "analog":
        return serialization.converters["json"].structure(
            time_lane_content, AnalogTimeLane
        )
    elif time_lane_type == "camera":
        return serialization.converters["json"].structure(
            time_lane_content, CameraTimeLane
        )
    else:
        raise ValueError(f"Unknown time lane type {time_lane_type}")


default_sequence_serializer = SequenceSerializer(
    iteration_serializer=default_iteration_configuration_serializer,
    iteration_constructor=default_iteration_configuration_constructor,
    time_lane_serializer=default_time_lane_serializer,
    time_lane_constructor=default_time_lane_constructor,
)

default_serializer = Serializer(
    sequence_serializer=default_sequence_serializer, device_configuration_serializers={}
)
"""A default serializer object for SQLExperimentSessionMaker,
It can read and store sequences that use steps to iterate over parameters and with shots 
containing digital, analog and camera time lanes. 
"""
