from typing import Any, Generic

from device.configuration import DeviceConfiguration, DeviceParameter
from single_atom_detector import SingleAtomDetector
from .atom_label import AtomLabel

ConfigurationName = str


class AtomDetectorConfiguration(DeviceConfiguration, Generic[AtomLabel]):
    """Holds the information needed to initialize an AtomDetector device.

    Attributes:
        detector_configurations: A dictionary of stored configurations that can be chosen from.
    """

    detector_configurations: dict[
        ConfigurationName, dict[AtomLabel, SingleAtomDetector]
    ]

    def get_device_init_args(
        self, configuration_name: ConfigurationName
    ) -> dict[DeviceParameter, Any]:
        return super().get_device_init_args() | {
            "single_atom_detectors": self.get_detector_configuration(configuration_name)
        }

    def get_device_type(self) -> str:
        return "AtomDetector"

    def get_detector_configuration(
        self, configuration_name: ConfigurationName
    ) -> dict[AtomLabel, SingleAtomDetector]:
        return self.detector_configurations[configuration_name]
