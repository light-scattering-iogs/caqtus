from caqtus.device import DeviceName
from caqtus.device.sequencer.configuration import (
    LaneValues,
    Constant,
    ChannelOutput,
    DeviceTrigger,
)
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


def test_3():
    d = DeviceTrigger("test", default=Constant(Expression("Disabled")))
    u = serialization.unstructure(d, ChannelOutput)
    s = serialization.structure(u, ChannelOutput)
    assert s == d


def test_4():
    u = {"device_name": "test", "type": "DeviceTrigger"}
    d = DeviceTrigger("test")
    s = serialization.structure(u, ChannelOutput)
    assert s == d


def test_5():
    lane_output = LaneValues("lane", default=None)

    u = serialization.unstructure(lane_output, ChannelOutput)
    s = serialization.structure(u, ChannelOutput)
    assert lane_output == s


def test_6():
    data = {
        "device_name": "Fringe stabilizer",
        "default": {"value": "Disabled"},
        "type": "DeviceTrigger",
    }
    result = serialization.converters["json"].structure(data, ChannelOutput)
    assert result == DeviceTrigger(
        device_name=DeviceName("Fringe stabilizer"),
        default=Constant(Expression("Disabled")),
    )


def test_7():
    data = {
        "lane": "421 cell \\ kill \\ shutter",
        "default": {"value": "Disabled"},
        "type": "LaneValues",
    }
    result = serialization.converters["json"].structure(data, ChannelOutput)
    assert result == LaneValues(
        "421 cell \\ kill \\ shutter", default=Constant(Expression("Disabled"))
    )
