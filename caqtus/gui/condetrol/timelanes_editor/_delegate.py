import abc
from collections.abc import Mapping, Set

from PySide6.QtWidgets import QStyledItemDelegate

from caqtus.device import DeviceName, DeviceConfiguration
from caqtus.gui.qtutil import QABCMeta


class TimeLaneDelegate(QStyledItemDelegate, metaclass=QABCMeta):
    """A delegate to display and edit the cells of a time lane."""

    def set_device_configurations(
        self, device_configurations: Mapping[DeviceName, DeviceConfiguration]
    ) -> None:
        """Set the device configurations.

        This method is called when the device configurations are updated.
        The delegate should use this information to update the appearance of the lane
        cells or editor if they depend on the device configurations.
        """

        pass

    def set_parameter_names(self, parameter_names: Set[str]) -> None:
        """Update the name of the parameters used in the sequence.

        This method is called when the parameter names are updated.
        The delegate should use this information to update the appearance of the lane
        cells or editors if they depend on the parameter names.
        """

        pass
