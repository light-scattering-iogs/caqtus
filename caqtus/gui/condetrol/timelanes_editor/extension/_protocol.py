from collections.abc import Mapping, Callable
from typing import Protocol, Optional, Any, TypeVar, TypeAlias

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget, QStyledItemDelegate

from caqtus.device import DeviceName, DeviceConfiguration
from caqtus.session import ParameterNamespace
from caqtus.session.shot import TimeLane
from .. import TimeLaneDelegate
from ..model import TimeLaneModel

L = TypeVar("L", bound=TimeLane)


class CondetrolLaneExtensionProtocol(Protocol):
    """Defines the operations necessary to extend Condetrol with new lanes."""

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
        self, lane: L, name: str, parent: Optional[QObject]
    ) -> TimeLaneModel[L, Any]:
        """Return the model for the given lane.

        This method is called when a lane needs to be displayed.
        The returned model will be used to provide the data from the lane to the view.
        """

        ...

    def get_lane_delegate(
        self,
        lane: L,
        lane_name: str,
    ) -> Optional[TimeLaneDelegate]:
        """Return a delegate for the given lane.

        This method is called when a lane needs to be displayed.
        The returned delegate will be used to paint the lane cells in the view and to
        provide editing capabilities.
        """

        ...
