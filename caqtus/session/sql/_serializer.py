from __future__ import annotations

import abc
import functools
from collections.abc import Callable
from typing import TypeVar

import attrs
from typing_extensions import Protocol

from caqtus.device import DeviceConfiguration
from caqtus.device.configuration.serializer import (
    DeviceConfigJSONSerializer,
)
from caqtus.types.iteration import (
    IterationConfiguration,
    StepsConfiguration,
)
from caqtus.types.timelane import TimeLanes
from caqtus.types.timelane._serializer import (
    TimeLaneSerializer,
)
from caqtus.utils import serialization
from caqtus.utils.serialization import JSON

T = TypeVar("T", bound=DeviceConfiguration)


class SerializerProtocol(Protocol):
    """Serialize and deserialize user objects."""

    @abc.abstractmethod
    def dump_device_configuration(
        self, config: DeviceConfiguration
    ) -> tuple[str, serialization.JSON]:
        raise NotImplementedError

    @abc.abstractmethod
    def load_device_configuration(
        self, tag: str, content: serialization.JSON
    ) -> DeviceConfiguration:
        raise NotImplementedError

    @abc.abstractmethod
    def construct_sequence_iteration(
        self, content: serialization.JSON
    ) -> IterationConfiguration:
        raise NotImplementedError

    @abc.abstractmethod
    def dump_sequence_iteration(
        self, iteration: IterationConfiguration
    ) -> serialization.JSON:
        raise NotImplementedError

    @abc.abstractmethod
    def unstructure_time_lanes(self, time_lanes: TimeLanes) -> serialization.JSON:
        raise NotImplementedError

    @abc.abstractmethod
    def structure_time_lanes(self, content: serialization.JSON) -> TimeLanes:
        raise NotImplementedError


@attrs.define
class Serializer(SerializerProtocol):
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

    def construct_sequence_iteration(
        self, content: serialization.JSON
    ) -> IterationConfiguration:
        return self.sequence_serializer.iteration_constructor(content)

    def dump_sequence_iteration(
        self, iteration: IterationConfiguration
    ) -> serialization.JSON:
        return self.sequence_serializer.iteration_serializer(iteration)

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

    def unstructure_time_lanes(self, time_lanes: TimeLanes) -> serialization.JSON:
        return self.time_lane_serializer.unstructure_time_lanes(time_lanes)

    def structure_time_lanes(self, content: serialization.JSON) -> TimeLanes:
        return self.time_lane_serializer.structure_time_lanes(content)


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
    iteration_content,
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
