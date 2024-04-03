from collections.abc import Callable, Mapping
from typing import TypeVar

import attrs

from caqtus.device import DeviceConfiguration
from .device_configuration_editor import (
    DeviceConfigurationEditor,
    DefaultDeviceConfigurationEditor,
)

C = TypeVar("C", bound=DeviceConfiguration)

DeviceConfigurationEditorFactory = Callable[[C], DeviceConfigurationEditor[C]]

DeviceConfigurationFactory = Callable[[], DeviceConfiguration]


@attrs.define
class DeviceConfigurationsPlugin:
    editor_factory: DeviceConfigurationEditorFactory
    configuration_factories: Mapping[str, DeviceConfigurationFactory]


def default_device_editor_factory(
    device_configuration: C,
) -> DeviceConfigurationEditor[C]:
    return DefaultDeviceConfigurationEditor(device_configuration)


default_device_configuration_plugin = DeviceConfigurationsPlugin(
    editor_factory=default_device_editor_factory,
    configuration_factories={},
)
