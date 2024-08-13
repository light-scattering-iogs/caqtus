"""This package defines widgets that are used to edit device configurations.

All editors must derive from :class:`DeviceConfigurationEditor`.
"""

from ._device_configuration_editor import (
    DeviceConfigurationEditor,
    FormDeviceConfigurationEditor,
)

__all__ = [
    "DeviceConfigurationEditor",
    "FormDeviceConfigurationEditor",
]
