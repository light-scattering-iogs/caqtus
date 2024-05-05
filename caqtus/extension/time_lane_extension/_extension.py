from collections.abc import Callable
from typing import TypeVar, Optional

import attrs

from caqtus.session.shot import TimeLane
from caqtus.utils.serialization import JSON

L = TypeVar("L", bound=TimeLane)


@attrs.frozen
class TimeLaneExtension:
    label: str = attrs.field(converter=str)
    lane_type: type[L] = attrs.field()
    dumper: Callable[[L], JSON] = attrs.field()
    loader: Callable[[JSON], L] = attrs.field()
    type_tag: Optional[str] = attrs.field(default=None)

    @lane_type.validator
    def _validate_lane_type(self, attribute, value):
        if not issubclass(value, TimeLane):
            raise ValueError(f"{value} is not a subclass of TimeLane")
