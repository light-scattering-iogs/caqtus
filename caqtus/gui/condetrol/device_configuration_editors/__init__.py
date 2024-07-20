"""This package defines widgets that are used to edit device configurations.

All editors must derive from :class:`DeviceConfigurationEditor`.
"""

from .configurations_editor import DeviceConfigurationsDialog
from .device_configuration_editor import (
    DeviceConfigurationEditor,
    FormDeviceConfigurationEditor,
)
from .sequencer_configuration_editor import SequencerConfigurationEditor

__all__ = [
    "DeviceConfigurationEditor",
    "SequencerConfigurationEditor",
    "FormDeviceConfigurationEditor",
    "DeviceConfigurationsDialog",
]
