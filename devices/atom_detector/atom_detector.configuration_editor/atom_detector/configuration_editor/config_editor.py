from atom_detector.configuration import AtomDetectorConfiguration
from device.configuration_editor import ConfigEditor


class AtomDetectorConfigEditor(ConfigEditor[AtomDetectorConfiguration]):
    def get_device_config(self) -> AtomDetectorConfiguration:
        return super().get_device_config()
