from collections.abc import Set
from typing import Any, NewType

from configuration_holder import ConfigurationHolder
from device.configuration import DeviceConfigurationAttrs, DeviceParameter
from settings_model import YAMLSerializable
from single_atom_detector import SingleAtomDetector
from util import attrs
from .atom_label import AtomLabel

ImagingConfigurationName = NewType("ImagingConfigurationName", str)

ImagingConfiguration = dict[AtomLabel, SingleAtomDetector]


@attrs.define(slots=False)
class AtomDetectorConfiguration(
    DeviceConfigurationAttrs,
    ConfigurationHolder[ImagingConfigurationName, ImagingConfiguration],
):
    """Holds the information needed to initialize an AtomDetector device."""

    def get_device_init_args(
        self, imaging_configurations_to_use: Set[ImagingConfigurationName]
    ) -> dict[DeviceParameter, Any]:
        return super().get_device_init_args() | {
            DeviceParameter("imaging_configurations"): {
                configuration_name: self[configuration_name]
                for configuration_name in imaging_configurations_to_use
            }
        }

    def get_device_type(self) -> str:
        return "AtomDetector"


YAMLSerializable.register_attrs_class(AtomDetectorConfiguration)
