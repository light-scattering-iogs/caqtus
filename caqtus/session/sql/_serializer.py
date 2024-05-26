from __future__ import annotations

import functools
from collections.abc import Callable
from typing import TypeVar

import attrs
from typing_extensions import Protocol

from caqtus.device import DeviceConfiguration
from caqtus.device.configuration.serializer import (
    DeviceConfigJSONSerializer,
    DeviceConfigJSONSerializerProtocol,
)
from caqtus.utils import serialization
from caqtus.utils.serialization import JSON
from caqtus.types.iteration import (
    IterationConfiguration,
    StepsConfiguration,
)
from ..shot import TimeLane
from caqtus.types.timelane.serializer import (
    TimeLaneSerializerProtocol,
    TimeLaneSerializer,
)

T = TypeVar("T", bound=DeviceConfiguration)


class SerializerProtocol(Protocol):
    sequence_serializer: SequenceSerializer
    device_configuration_serializer: DeviceConfigJSONSerializerProtocol
    time_lane_serializer: TimeLaneSerializerProtocol

    def dump_device_configuration(
        self, config: DeviceConfiguration
    ) -> tuple[str, serialization.JSON]:
        return self.device_configuration_serializer.dump_device_configuration(config)

    def load_device_configuration(
        self, tag: str, content: serialization.JSON
    ) -> DeviceConfiguration:
        return self.device_configuration_serializer.load_device_configuration(
            tag, content
        )

    def construct_sequence_iteration(
        self, content: serialization.JSON
    ) -> IterationConfiguration:
        return self.sequence_serializer.iteration_constructor(content)

    def dump_sequence_iteration(
        self, iteration: IterationConfiguration
    ) -> serialization.JSON:
        return self.sequence_serializer.iteration_serializer(iteration)

    def dump_time_lane(self, lane: TimeLane) -> serialization.JSON:
        return self.time_lane_serializer.dump(lane)

    def construct_time_lane(self, content: serialization.JSON) -> TimeLane:
        return self.time_lane_serializer.load(content)


@attrs.define
class Serializer(SerializerProtocol):
    """Serialize and deserialize user objects."""

    sequence_serializer: SequenceSerializer
    device_configuration_serializer: DeviceConfigJSONSerializer
    time_lane_serializer: TimeLaneSerializer

    @classmethod
    def default(cls) -> Serializer:
        return Serializer(
            sequence_serializer=default_sequence_serializer,
            device_configuration_serializer=DeviceConfigJSONSerializer(),
            time_lane_serializer=TimeLaneSerializer(),
        )

    def register_device_configuration(
        self,
        config_type: type[T],
        dumper: Callable[[T], JSON],
        constructor: Callable[[JSON], T],
    ) -> None:
        self.device_configuration_serializer.register_device_configuration(
            config_type, dumper, constructor
        )

    def register_iteration_configuration_serializer(
        self,
        dumper: Callable[[IterationConfiguration], serialization.JSON],
        constructor: Callable[[serialization.JSON], IterationConfiguration],
    ) -> None:
        self.sequence_serializer = SequenceSerializer(
            iteration_serializer=dumper,
            iteration_constructor=constructor,
        )


@attrs.frozen
class SequenceSerializer:
    iteration_serializer: Callable[[IterationConfiguration], serialization.JSON]
    iteration_constructor: Callable[[serialization.JSON], IterationConfiguration]


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


default_sequence_serializer = SequenceSerializer(
    iteration_serializer=default_iteration_configuration_serializer,
    iteration_constructor=default_iteration_configuration_constructor,
)
