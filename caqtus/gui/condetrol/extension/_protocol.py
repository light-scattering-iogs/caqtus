from collections.abc import Mapping
from typing import Protocol, TypeVar, runtime_checkable, Optional, Any

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget, QStyledItemDelegate

from caqtus.device import DeviceConfiguration, DeviceName
from caqtus.session import ParameterNamespace
from caqtus.session.shot import TimeLane
from ..device_configuration_editors import DeviceConfigurationEditor
from ..timelanes_editor import TimeLaneModel

C = TypeVar("C", bound=DeviceConfiguration)
L = TypeVar("L", bound=TimeLane)


@runtime_checkable
class CondetrolExtensionProtocol(Protocol):
    """Defines the operations an extension must implement to be used by Condetrol."""

    def get_device_configuration_editor(
        self, device_configuration: C
    ) -> DeviceConfigurationEditor[C]:
        """Create an editor for the given device configuration.

        This method is called when the user wants to edit a device configuration.
        The returned editor will be used to display and modify the device configuration.
        """

        ...

    def available_new_configurations(self) -> set[str]:
        """Return the new configurations that can be created.

        This method is called when the user wants to create a new device configuration.
        The user will be able to choose one of the returned labels.
        """

        ...

    def create_new_device_configuration(
        self, configuration_label: str
    ) -> DeviceConfiguration:
        """Create a new device configuration.

        This method is called when the user wants to create a new device configuration.
        The label of the configuration to create is passed as an argument.
        """

        ...

    def available_new_lanes(self) -> set[str]:
        """Return the new lanes that can be created.

        This method is called when the user clicks on the "Add lane" button and needs
        to choose the type of lane to create.
        """

        ...

    def create_new_lane(self, lane_label: str, steps: int) -> TimeLane:
        """Create a new lane.

        This method is called when the user wants to create a new lane.
        The label of the lane to create and the number of steps are passed as arguments.
        """

        ...

    def get_lane_model(
        self, name: str, lane: L, parent: Optional[QObject]
    ) -> TimeLaneModel[L, Any]:
        """Return the model for the given lane.

        This method is called when a lane needs to be displayed.
        The returned model will be used to provide the data from the lane to the view.
        """

        ...

    def get_lane_delegate(
        self,
        lane_name: str,
        lane: L,
        device_configurations: Mapping[DeviceName, DeviceConfiguration],
        sequencer_parameters: ParameterNamespace,
        parent: QWidget,
    ) -> Optional[QStyledItemDelegate]:
        """Return a delegate for the given lane.

        This method is called when a lane needs to be displayed.
        The returned delegate will be used to paint the lane cells in the view and to
        provide editing capabilities.
        """

        ...
