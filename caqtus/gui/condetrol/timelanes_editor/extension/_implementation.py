import functools
from collections.abc import Mapping, Callable
from typing import Optional, TypeAlias, Protocol, TypeVar, Any

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget, QStyledItemDelegate

from caqtus.device import DeviceName, DeviceConfiguration
from caqtus.session import ParameterNamespace
from caqtus.session.shot import (
    TimeLane,
    DigitalTimeLane,
    AnalogTimeLane,
    CameraTimeLane,
)
from caqtus.types.expression import Expression
from ._protocol import CondetrolLaneExtensionProtocol
from ..analog_lane_model import AnalogTimeLaneModel
from ..camera_lane_model import CameraTimeLaneModel
from ..digital_lane_delegate import DigitalTimeLaneDelegate
from ..digital_lane_model import DigitalTimeLaneModel
from ..model import TimeLaneModel

L = TypeVar("L", bound=TimeLane)

LaneFactory: TypeAlias = Callable[[int], TimeLane]


class LaneDelegateFactory(Protocol[L]):
    """A factory for lane delegates."""

    def __call__(
        self,
        lane: L,
        lane_name: str,
        device_configurations: Mapping[DeviceName, DeviceConfiguration],
        sequence_parameters: ParameterNamespace,
        parent: QWidget,
    ) -> Optional[QStyledItemDelegate]:
        """Create a delegate for the lane passed as argument."""
        ...


class LaneModelFactory(Protocol[L]):
    def __call__(
        self,
        lane: L,
        lane_name: str,
        parent: Optional[QWidget],
    ) -> TimeLaneModel[L, Any]:
        """Create a delegate for the lane passed as argument."""
        ...


class CondetrolLaneExtension(CondetrolLaneExtensionProtocol):
    def __init__(self):
        self.get_lane_delegate = functools.singledispatch(default_lane_delegate_factory)
        self.get_lane_model = functools.singledispatch(default_lane_model_factory)
        self._lane_factories: dict[str, LaneFactory] = {
            "Digital": create_digital_lane,
            "Analog": create_analog_lane,
            "Camera": create_camera_lane,
        }

    def register_lane_factory(self, lane_label: str, factory: LaneFactory) -> None:
        self._lane_factories[lane_label] = factory

    def register_lane_delegate_factory(
        self, lane_type: type[L], factory: LaneDelegateFactory[L]
    ) -> None:
        self.get_lane_delegate.register(lane_type)(factory)

    def register_lane_model_factory(
        self, lane_type: type[L], factory: LaneModelFactory[L]
    ) -> None:
        self.get_lane_model.register(lane_type)(factory)

    def available_new_lanes(self) -> set[str]:
        return set(self._lane_factories.keys())

    def create_new_lane(self, lane_label: str, steps: int) -> TimeLane:
        return self._lane_factories[lane_label](steps)


def default_lane_model_factory(
    lane, name: str, parent: Optional[QObject]
) -> TimeLaneModel:
    if not isinstance(lane, TimeLane):
        raise TypeError(f"Expected a TimeLane, got {type(lane)}.")

    if isinstance(lane, DigitalTimeLane):
        model = DigitalTimeLaneModel(name, parent)
        model.set_lane(lane)
        return model
    elif isinstance(lane, AnalogTimeLane):
        model = AnalogTimeLaneModel(name, parent)
        model.set_lane(lane)
        return model
    elif isinstance(lane, CameraTimeLane):
        model = CameraTimeLaneModel(name, parent)
        model.set_lane(lane)
        return model
    else:
        raise NotImplementedError(
            f"Don't know how to provide a model for {type(lane)}."
        )


def default_lane_delegate_factory(
    lane: TimeLane,
    lane_name: str,
    device_configurations: Mapping[DeviceName, DeviceConfiguration],
    sequence_parameters: ParameterNamespace,
    parent: QWidget,
) -> Optional[QStyledItemDelegate]:
    if isinstance(lane, DigitalTimeLane):
        return DigitalTimeLaneDelegate(parent)
    else:
        return None


def create_digital_lane(number_steps: int) -> DigitalTimeLane:
    return DigitalTimeLane([False] * number_steps)


def create_analog_lane(number_steps: int) -> AnalogTimeLane:
    return AnalogTimeLane([Expression("...")] * number_steps)


def create_camera_lane(number_steps: int) -> CameraTimeLane:
    return CameraTimeLane([None] * number_steps)
