from collections.abc import Callable
from typing import Optional

import attrs

from caqtus.gui.condetrol.timelanes_editor.extension import (
    LaneFactory,
    LaneModelFactory,
    LaneDelegateFactory,
)

# noinspection PyPep8Naming
from caqtus.types.timelane import TimeLaneType as L, TimeLane
from caqtus.utils.serialization import JSON


def no_lane_delegate_factory(lane: TimeLane, lane_name: str) -> None:
    return None


@attrs.frozen
class TimeLaneExtension:
    """Contains the information necessary to extend Condetrol with a new lane.

    Attributes:
        label: An identifier for this type of lane to be displayed to the user.
        lane_type: The type of lane to be created.
        dumper: A function to serialize the lane to JSON.
            When a lane with the corresponding type needs to be saved, this function
            will be called and the result will be stored.
            The returned value must be a dictionary that can be serialized to JSON.
            The dictionary will be added a "type" key to identify the lane type.
        loader: A function to deserialize the lane from JSON.
            When JSON data with the corresponding "type" key is loaded, this function
            will be called to create a lane.
        lane_factory: A factory function to create a new lane when the user wants to
            create a lane with this label.
            The factory will be called with the number of steps the lane must have.
        lane_delegate_factory: A factory function to create a delegate for the lane.
            The factory will be called when the lane is displayed in the editor.
            The delegate returned by the factory will be used for custom painting and
            editing of the lane.
            The default lane delegate factory returns None.
        lane_model_factory: A factory function to create a model for the lane.
            The model will be used to provide the data from the lane to the view.
    """

    label: str = attrs.field(converter=str)
    lane_type: type[L] = attrs.field()
    dumper: Callable[[L], JSON] = attrs.field()
    loader: Callable[[JSON], L] = attrs.field()
    lane_factory: LaneFactory[L] = attrs.field()
    lane_model_factory: LaneModelFactory[L] = attrs.field()
    lane_delegate_factory: LaneDelegateFactory[L] = attrs.field(
        default=no_lane_delegate_factory
    )
    type_tag: Optional[str] = attrs.field(default=None)

    @lane_type.validator
    def _validate_lane_type(self, attribute, value):
        if not issubclass(value, TimeLane):
            raise ValueError(f"{value} is not a subclass of TimeLane")
