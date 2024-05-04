import functools
from collections.abc import Callable
from typing import TypeVar

from caqtus.device import DeviceConfiguration
from ._protocol import CondetrolExtensionProtocol
from ..device_configuration_editors.device_configuration_editor import (
    FormDeviceConfigurationEditor,
    DeviceConfigurationEditor,
)
from ..timelanes_editor.extension import CondetrolLaneExtension

C = TypeVar("C", bound=DeviceConfiguration)


class CondetrolExtension(CondetrolExtensionProtocol):
    def __init__(self):
        self.lane_extension = CondetrolLaneExtension()
        self.get_device_configuration_editor = functools.singledispatch(
            get_default_device_configuration_editor
        )

        self.configuration_factories: dict[str, Callable[[], DeviceConfiguration]] = {}

    def register_device_configuration_editor(
        self,
        configuration_type: type[C],
        editor_type: Callable[[C], DeviceConfigurationEditor[C]],
    ) -> None:
        self.get_device_configuration_editor.register(configuration_type)(editor_type)

    def register_configuration_factory(
        self, configuration_label: str, factory: Callable[[], DeviceConfiguration]
    ) -> None:
        self.configuration_factories[configuration_label] = factory

    def available_new_configurations(self) -> set[str]:
        return set(self.configuration_factories.keys())

    def create_new_device_configuration(
        self, configuration_label: str
    ) -> DeviceConfiguration:
        return self.configuration_factories[configuration_label]()


def get_default_device_configuration_editor(
    configuration,
) -> DeviceConfigurationEditor[DeviceConfiguration]:
    if not isinstance(configuration, DeviceConfiguration):
        raise TypeError(f"Expected a DeviceConfiguration, got {type(configuration)}.")
    return FormDeviceConfigurationEditor(configuration)
