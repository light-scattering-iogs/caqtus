from core.session.shot.timelane import AnalogTimeLane, Ramp
from core.types.expression import Expression
from util import serialization


def test():
    lane = AnalogTimeLane(
        [(Expression("0 mW"), 1), (Ramp(), 2), (Expression("0.7 mW"), 1)]
    )
    s = serialization.converters["json"].unstructure(lane, AnalogTimeLane)
    print(s)
    o = serialization.converters["json"].structure(s, AnalogTimeLane)
    assert o == lane, (o, lane)
