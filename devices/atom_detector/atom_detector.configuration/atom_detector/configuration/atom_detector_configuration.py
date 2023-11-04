import datetime
from collections.abc import Set
from typing import Any, TypedDict, NewType

from configuration_holder import ConfigurationHolder
from device.configuration import DeviceConfiguration, DeviceParameter
from single_atom_detector import SingleAtomDetector
from .atom_label import AtomLabel

ImagingConfigurationName = NewType("ImagingConfigurationName", str)

ImagingConfiguration = dict[AtomLabel, SingleAtomDetector]


class DetectorConfigurationInfo(TypedDict):
    configuration: dict[AtomLabel, SingleAtomDetector]
    modification_date: datetime.datetime


class AtomDetectorConfiguration(
    DeviceConfiguration,
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
