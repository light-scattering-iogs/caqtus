import attrs
from .timelane import TimeLane
from core.types.expression import Expression


@attrs.define(eq=False, repr=False)
class DigitalTimeLane(TimeLane[bool | Expression]):
    pass
