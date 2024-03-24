from collections.abc import Mapping
from typing import Protocol, Optional

import attrs
from PySide6.QtWidgets import QWidget, QStyledItemDelegate

from caqtus.device import DeviceConfigurationAttrs, DeviceName
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


class LaneFactory(Protocol):
    def __call__(self, number_steps: int) -> TimeLane: ...


class LaneModelFactory(Protocol):
    """A factory for lane models."""

    def __call__(self, lane: TimeLane) -> type[TimeLaneModel]: ...


class LaneDelegateFactory(Protocol):
    """A factory for lane delegates."""

    def __call__(
        self,
        lane_name: str,
        lane: TimeLane,
        device_configurations: Mapping[DeviceName, DeviceConfigurationAttrs],
        sequence_parameters: ParameterNamespace,
        parent: QWidget,
    ) -> Optional[QStyledItemDelegate]: ...


@attrs.define
class TimeLanesPlugin:
    """Specify how the display and edit time lanes.

    Attributes:
        lane_factories: A mapping from type of lanes to lane factories.
        When the user wants to add a new lane, they can choose from the keys of this
        mapping and the corresponding factory will be called to create the lane.
        lane_model_factory: A factory for lane models.
        lane_delegate_factory: A factory for lane delegates.
    """

    lane_factories: Mapping[str, LaneFactory]
    lane_model_factory: LaneModelFactory
    lane_delegate_factory: LaneDelegateFactory


def default_lane_delegate_factory(
    lane_name: str,
    lane: TimeLane,
    device_configurations: Mapping[DeviceName, DeviceConfigurationAttrs],
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


default_time_lanes_plugin = TimeLanesPlugin(
    lane_factories={
        "Digital": create_digital_lane,
        "Analog": create_analog_lane,
        "Camera": create_camera_lane,
    },
    lane_model_factory=default_lane_model_factory,
    lane_delegate_factory=default_lane_delegate_factory,
)
