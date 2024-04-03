from __future__ import annotations

from collections.abc import Mapping, Callable
from typing import Protocol, Optional, TypeAlias

import attrs
from PySide6.QtWidgets import QWidget, QStyledItemDelegate

from caqtus.device import DeviceConfiguration, DeviceName
from caqtus.gui.condetrol.timelanes_editor.digital_lane_delegate import (
    DigitalTimeLaneDelegate,
)
from caqtus.gui.condetrol.timelanes_editor.model import TimeLaneModel
from caqtus.session import ParameterNamespace
from caqtus.session.shot import (
    AnalogTimeLane,
    CameraTimeLane,
)
from caqtus.session.shot import TimeLane, DigitalTimeLane
from caqtus.types.expression import Expression
from .analog_lane_model import AnalogTimeLaneModel
from .camera_lane_model import CameraTimeLaneModel
from .digital_lane_model import DigitalTimeLaneModel

LaneFactory: TypeAlias = Callable[[int], TimeLane]

LaneModelFactory: TypeAlias = Callable[[TimeLane], type[TimeLaneModel]]


class LaneDelegateFactory(Protocol):
    """A factory for lane delegates."""

    def __call__(
        self,
        lane_name: str,
        lane: TimeLane,
        device_configurations: Mapping[DeviceName, DeviceConfiguration],
        sequence_parameters: ParameterNamespace,
        parent: QWidget,
    ) -> Optional[QStyledItemDelegate]:
        """Create a delegate for the lane passed as argument."""
        ...


@attrs.define
class TimeLanesPlugin:
    """Allows to customize how lanes are used in the time lane's editor.

    Parameters
    ----------
    lane_factories
        A mapping from type of lanes to lane factories.
        When the user wants to add a new lane, they can choose from the keys of this
        mapping and the corresponding factory will be called to create the lane.
        The factory should take an integer as argument and return a new lane with that
        number of steps.
    lane_model_factory
        A factory for lane models.
        When a lane needs to be displayed, this function will be called with the lane as
        argument and the returned :class:`TimeLaneModel` will be used to provide the
        data from the lane to the view.
    lane_delegate_factory
        A factory for lane delegates.
        When a lane needs to be displayed, this function will be called and the delegate
        returned will be used to paint the lane cells in the view and to provide editing
        capabilities.
    """

    lane_factories: Mapping[str, LaneFactory]
    lane_model_factory: LaneModelFactory
    lane_delegate_factory: LaneDelegateFactory


def default_lane_delegate_factory(
    lane_name: str,
    lane: TimeLane,
    device_configurations: Mapping[DeviceName, DeviceConfiguration],
    sequence_parameters: ParameterNamespace,
    parent: QWidget,
) -> Optional[QStyledItemDelegate]:
    if isinstance(lane, DigitalTimeLane):
        return DigitalTimeLaneDelegate(parent)
    else:
        return None


def default_lane_model_factory(lane: TimeLane) -> type[TimeLaneModel]:
    match lane:
        case DigitalTimeLane():
            return DigitalTimeLaneModel
        case AnalogTimeLane():
            return AnalogTimeLaneModel
        case CameraTimeLane():
            return CameraTimeLaneModel
        case _:
            raise NotImplementedError


def create_digital_lane(number_steps: int) -> DigitalTimeLane:
    return DigitalTimeLane([False] * number_steps)


def create_analog_lane(number_steps: int) -> AnalogTimeLane:
    return AnalogTimeLane([Expression("...")] * number_steps)


def create_camera_lane(number_steps: int) -> CameraTimeLane:
    return CameraTimeLane([None] * number_steps)


#: A default instance of :class:`TimeLanesPlugin` that knows how to handle digital,
#: analog, and camera lanes.
default_time_lanes_plugin = TimeLanesPlugin(
    lane_factories={
        "Digital": create_digital_lane,
        "Analog": create_analog_lane,
        "Camera": create_camera_lane,
    },
    lane_model_factory=default_lane_model_factory,
    lane_delegate_factory=default_lane_delegate_factory,
)
