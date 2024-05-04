import functools
from collections.abc import Callable, Mapping
from typing import TypeVar, TypeAlias, Optional, Protocol

from PySide6.QtWidgets import QWidget, QStyledItemDelegate

from caqtus.device import DeviceConfiguration, DeviceName
from caqtus.gui.condetrol.extension import CondetrolExtensionProtocol
from caqtus.session import ParameterNamespace
from caqtus.session.shot import (
    DigitalTimeLane,
    AnalogTimeLane,
    CameraTimeLane,
    TimeLane,
)
from caqtus.types.expression import Expression
from ..device_configuration_editors.device_configuration_editor import (
    FormDeviceConfigurationEditor,
    DeviceConfigurationEditor,
)
from ..timelanes_editor import TimeLaneModel, DigitalTimeLaneModel
from ..timelanes_editor.analog_lane_model import AnalogTimeLaneModel
from ..timelanes_editor.camera_lane_model import CameraTimeLaneModel
from ..timelanes_editor.digital_lane_delegate import DigitalTimeLaneDelegate

C = TypeVar("C", bound=DeviceConfiguration)
L = TypeVar("L", bound=TimeLane)

LaneFactory: TypeAlias = Callable[[int], TimeLane]
LaneModelFactory: TypeAlias = Callable[[L], type[TimeLaneModel[L]]]


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


class CondetrolExtension(CondetrolExtensionProtocol):
    def __init__(self):
        self.get_device_configuration_editor = functools.singledispatch(
            get_default_device_configuration_editor
        )
        self.configuration_factories: dict[str, Callable[[], DeviceConfiguration]] = {}
        self.lane_factories: dict[str, LaneFactory] = {
            "Digital": create_digital_lane,
            "Analog": create_analog_lane,
            "Camera": create_camera_lane,
        }
        self.get_lane_delegate = functools.singledispatch(default_lane_delegate_factory)

    def register_device_configuration_editor(
        self,
        configuration_type: type[C],
        editor_type: Callable[[C], DeviceConfigurationEditor[C]],
    ) -> None:
        self.get_device_configuration_editor.register(configuration_type)(editor_type)

    def register_configuration_factory(
        self, configuration_label: str, factory: Callable[[], DeviceConfiguration]
    ) -> None:
        self.configuration_factories[configuration_label] = factory

    def register_lane_factory(self, lane_label: str, factory: LaneFactory) -> None:
        self.lane_factories[lane_label] = factory

    def register_lane_delegate_factory(
        self, lane_type: type[L], factory: LaneDelegateFactory[L]
    ) -> None:
        self.get_lane_delegate.register(lane_type)(factory)

    def available_new_configurations(self) -> set[str]:
        return set(self.configuration_factories.keys())

    def create_new_device_configuration(
        self, configuration_label: str
    ) -> DeviceConfiguration:
        return self.configuration_factories[configuration_label]()

    def available_new_lanes(self) -> set[str]:
        return set(self.lane_factories.keys())

    def create_new_lane(self, lane_label: str, steps: int) -> TimeLane:
        return self.lane_factories[lane_label](steps)


def get_default_device_configuration_editor(
    configuration,
) -> DeviceConfigurationEditor[DeviceConfiguration]:
    if not isinstance(configuration, DeviceConfiguration):
        raise TypeError(f"Expected a DeviceConfiguration, got {type(configuration)}.")
    return FormDeviceConfigurationEditor(configuration)


def create_digital_lane(number_steps: int) -> DigitalTimeLane:
    return DigitalTimeLane([False] * number_steps)


def create_analog_lane(number_steps: int) -> AnalogTimeLane:
    return AnalogTimeLane([Expression("...")] * number_steps)


def create_camera_lane(number_steps: int) -> CameraTimeLane:
    return CameraTimeLane([None] * number_steps)


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


def default_lane_model_factory(lane) -> type[TimeLaneModel]:
    if not isinstance(lane, TimeLane):
        raise TypeError(f"Expected a TimeLane, got {type(lane)}.")

    if isinstance(lane, DigitalTimeLane):
        return DigitalTimeLaneModel
    elif isinstance(lane, AnalogTimeLane):
        return AnalogTimeLaneModel
    elif isinstance(lane, CameraTimeLane):
        return CameraTimeLaneModel
    else:
        raise NotImplementedError(f"Don't know how to handle {type(lane)}.")
