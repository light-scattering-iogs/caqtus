from core.compilation import DigitalLaneCompiler, VariableNamespace
from core.device.sequencer.instructions import Pattern
from core.session.shot import DigitalTimeLane
from core.types.expression import Expression


def test_0():
    lane = DigitalTimeLane([(True, 1), (False, 1)])
    lane_compiler = DigitalLaneCompiler(lane)
    result = lane_compiler.compile([0, 1, 2], VariableNamespace(), 1)
    assert result == Pattern([True]) * 1_000_000_000 + Pattern([False]) * 1_000_000_000


def test_1():
    lane = DigitalTimeLane([(Expression("a"), 1), (Expression("b"), 1)])
    lane_compiler = DigitalLaneCompiler(lane)
    result = lane_compiler.compile(
        [0, 1, 2], VariableNamespace({"a": True, "b": False}), 1
    )

    assert result == Pattern([True]) * 1_000_000_000 + Pattern([False]) * 1_000_000_000


def test_2():
    lane = DigitalTimeLane([(True, 2), (False, 1)])
    lane_compiler = DigitalLaneCompiler(lane)
    result = lane_compiler.compile([0, 1, 2, 3], VariableNamespace(), 1)
    assert (
        result == Pattern([True]) * 2_000_000_000 + Pattern([False]) * 1_000_000_000
    ), str(result)
