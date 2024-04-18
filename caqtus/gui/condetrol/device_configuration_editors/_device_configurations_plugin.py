from __future__ import annotations

import functools
from collections.abc import Callable
from typing import TypeVar

import attrs

from caqtus.device import DeviceConfiguration
from .device_configuration_editor import (
    DeviceConfigurationEditor,
    DefaultDeviceConfigurationEditor,
)

C = TypeVar("C", bound=DeviceConfiguration)


DeviceConfigurationFactory = Callable[[], DeviceConfiguration]


@attrs.define(slots=False)
class DeviceConfigurationsPlugin:
    configuration_factories: dict[str, DeviceConfigurationFactory]

    @classmethod
    def default(cls) -> DeviceConfigurationsPlugin:
        return cls(configuration_factories={})

    def __attrs_post_init__(self):
        self.editor_factory = functools.singledispatch(DefaultDeviceConfigurationEditor)

    def register_default_configuration(
        self, configuration_label: str, factory: DeviceConfigurationFactory
    ) -> None:
        self.configuration_factories[configuration_label] = factory

    def register_editor(
        self,
        device_config_type: type[C],
        editor_factory: Callable[[C], DeviceConfigurationEditor[C]],
    ) -> None:
        self.editor_factory.register(device_config_type)(editor_factory)

    def create_editor(self, device_configuration: C) -> DeviceConfigurationEditor[C]:
        return self.editor_factory(device_configuration)

    def available_configuration_types(self) -> set[str]:
        return set(self.configuration_factories.keys())

    def create_device_configuration(
        self, configuration_type: str
    ) -> DeviceConfiguration:
        return self.configuration_factories[configuration_type]()
