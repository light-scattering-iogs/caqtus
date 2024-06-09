from caqtus.device import DeviceName
from caqtus.device.sequencer.configuration import (
    LaneValues,
    Constant,
    ChannelOutput,
    DeviceTrigger,
    CalibratedAnalogMapping,
    Advance,
    Delay,
    BroadenLeft,
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


def test_8():
    lane = CalibratedAnalogMapping(
        input_=Constant(Expression("0 V")),
        output_units="V",
        input_units="V",
        measured_data_points=((0.0, 0.0), (1.0, 1.0), (2.0, 2.0)),
    )
    u = serialization.unstructure(lane, ChannelOutput)
    reconstructed = serialization.structure(u, ChannelOutput)
    assert lane == reconstructed


def test_9():
    advance = Advance(
        input_=Constant(Expression("0 V")),
        advance=Expression("10 ms"),
    )
    u = serialization.unstructure(advance, ChannelOutput)
    reconstructed = serialization.structure(u, ChannelOutput)
    assert advance == reconstructed


def test_10():
    delay = Delay(
        input_=Constant(Expression("0 V")),
        delay=Expression("10 ms"),
    )
    u = serialization.unstructure(delay, ChannelOutput)
    reconstructed = serialization.structure(u, ChannelOutput)
    assert delay == reconstructed


def test_11():
    broaden_left = BroadenLeft(
        input_=Constant(Expression("0 V")),
        width=Expression("10 ms"),
    )
    u = serialization.unstructure(broaden_left, ChannelOutput)
    reconstructed = serialization.structure(u, ChannelOutput)
    assert broaden_left == reconstructed
