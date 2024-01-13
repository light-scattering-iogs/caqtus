from core.types.expression import Expression
from .timelane import TimeLane


class Ramp:
    pass


class AnalogTimeLane(TimeLane[Expression | Ramp]):
    pass
