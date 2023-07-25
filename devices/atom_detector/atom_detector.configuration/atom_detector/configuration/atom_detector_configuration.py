import datetime
from typing import Any, TypedDict, NewType

from configuration_holder import ConfigurationHolder
from device.configuration import DeviceConfiguration, DeviceParameter
from single_atom_detector import SingleAtomDetector
from .atom_label import AtomLabel

ConfigurationName = NewType("ConfigurationName", str)

DetectorConfiguration = dict[AtomLabel, SingleAtomDetector]


class DetectorConfigurationInfo(TypedDict):
    configuration: dict[AtomLabel, SingleAtomDetector]
    modification_date: datetime.datetime


class AtomDetectorConfiguration(
    DeviceConfiguration, ConfigurationHolder[ConfigurationName, DetectorConfiguration]
):
    """Holds the information needed to initialize an AtomDetector device."""

    detector_configurations: dict[ConfigurationName, DetectorConfigurationInfo]

    def get_device_init_args(
        self, configuration_name: ConfigurationName
    ) -> dict[DeviceParameter, Any]:
        return super().get_device_init_args() | {
            "single_atom_detectors": self[configuration_name]
        }

    def get_device_type(self) -> str:
        return "AtomDetector"

    def remove_configuration(self, configuration_name: ConfigurationName):
        """Remove a configuration from the configuration dictionary."""

        del self.detector_configurations[configuration_name]
