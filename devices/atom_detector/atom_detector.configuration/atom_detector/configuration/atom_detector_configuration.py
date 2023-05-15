import copy
import datetime
from typing import Any, Generic, NamedTuple

from device.configuration import DeviceConfiguration, DeviceParameter
from single_atom_detector import SingleAtomDetector
from validate_arguments import validate_arguments
from .atom_label import AtomLabel

ConfigurationName = str


class DetectorConfigurationInfo(NamedTuple):
    configuration: dict[AtomLabel, SingleAtomDetector]
    modification_date: datetime.datetime


class AtomDetectorConfiguration(DeviceConfiguration, Generic[AtomLabel]):
    """Holds the information needed to initialize an AtomDetector device."""

    detector_configurations: dict[ConfigurationName, DetectorConfigurationInfo]

    def get_device_init_args(
        self, configuration_name: ConfigurationName
    ) -> dict[DeviceParameter, Any]:
        return super().get_device_init_args() | {
            "single_atom_detectors": self.get_configuration(configuration_name)
        }

    def get_device_type(self) -> str:
        return "AtomDetector"

    def get_configuration(
        self, configuration_name: ConfigurationName
    ) -> dict[AtomLabel, SingleAtomDetector]:
        """Return a copy of the configuration associated with a given name."""

        return copy.deepcopy(
            self._get_configuration_info(configuration_name).configuration
        )

    def _get_configuration_info(
        self, configuration_name: ConfigurationName
    ) -> DetectorConfigurationInfo:
        try:
            return self.detector_configurations[configuration_name]
        except KeyError:
            raise KeyError(
                f"There is no configuration matching the name '{configuration_name}'"
            )

    @validate_arguments
    def set_configuration(
        self,
        configuration_name: ConfigurationName,
        configuration: dict[AtomLabel, SingleAtomDetector],
    ):
        """Set the value of a detector configuration at a given name."""

        self.detector_configurations[configuration_name] = DetectorConfigurationInfo(
            configuration=configuration, modification_date=datetime.datetime.now()
        )
