import functools
from collections.abc import Callable
from typing import Optional, TypeAlias, Protocol, TypeVar, Any

from PySide6.QtWidgets import QStyledItemDelegate

from caqtus.session.shot import (
    TimeLane,
)
from caqtus.types.timelane import TimeLanes
from caqtus.types.timelane.serializer import TimeLaneSerializer
from caqtus.utils import serialization
from ._protocol import CondetrolLaneExtensionProtocol
from ..model import TimeLaneModel

L = TypeVar("L", bound=TimeLane)

LaneFactory: TypeAlias = Callable[[int], L]


class LaneDelegateFactory(Protocol[L]):
    """A factory for lane delegates."""

    def __call__(
        self,
        lane: L,
        lane_name: str,
    ) -> Optional[QStyledItemDelegate]:
        """Create a delegate for the lane passed as argument."""
        ...


class LaneModelFactory(Protocol[L]):
    def __call__(
        self,
        lane: L,
        lane_name: str,
    ) -> TimeLaneModel[L, Any]:
        """Create a delegate for the lane passed as argument."""
        ...


class CondetrolLaneExtension(CondetrolLaneExtensionProtocol):
    def __init__(self):
        self.get_lane_delegate = functools.singledispatch(default_lane_delegate_factory)
        self.get_lane_model = functools.singledispatch(default_lane_model_factory)
        self._lane_factories: dict[str, LaneFactory] = {}
        self._lane_serializer = TimeLaneSerializer()

    def set_lane_serializer(self, serializer: TimeLaneSerializer) -> None:
        self._lane_serializer = serializer

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
        lane = self._lane_factories[lane_label](steps)
        if not isinstance(lane, TimeLane):
            raise TypeError(f"Expected a TimeLane, got {type(lane)}.")
        if len(lane) != steps:
            raise ValueError(
                f"Expected a lane with {steps} steps, got {len(lane)} steps."
            )
        return lane

    def unstructure_time_lanes(self, time_lanes: TimeLanes) -> serialization.JSON:
        return self._lane_serializer.unstructure_time_lanes(time_lanes)

    def structure_time_lanes(self, content: serialization.JSON) -> TimeLanes:
        return self._lane_serializer.structure_time_lanes(content)


def default_lane_model_factory(lane, name: str) -> TimeLaneModel:
    if not isinstance(lane, TimeLane):
        raise TypeError(f"Expected a TimeLane, got {type(lane)}.")

    raise NotImplementedError(f"Don't know how to provide a model for {type(lane)}.")


def default_lane_delegate_factory(
    lane,
    lane_name: str,
) -> Optional[QStyledItemDelegate]:
    return None
