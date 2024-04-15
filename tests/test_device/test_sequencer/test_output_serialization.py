from caqtus.device.sequencer.configuration import LaneValues, Constant, ChannelOutput
from caqtus.types.expression import Expression
from caqtus.utils import serialization


def test_0():
    lane_output = LaneValues("lane", default=Constant(Expression("Disabled")))

    u = serialization.unstructure(lane_output, ChannelOutput)
    s = serialization.structure(u, ChannelOutput)
    assert lane_output == s


def test_1():
    u = {"default": "Disabled", "lane": "lane", "type": "LaneValues"}
    lane_output = LaneValues("lane", default=Constant(Expression("Disabled")))
    s = serialization.structure(u, ChannelOutput)
    assert lane_output == s


def test_2():
    c = Constant(value=Expression("Disabled"))
    u = serialization.unstructure(c, ChannelOutput)
    assert u["type"] == "Constant"
