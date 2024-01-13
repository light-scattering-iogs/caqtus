from core.compilation.lane_compilers import DigitalLaneCompiler
from core.compilation import VariableNamespace
from core.device.sequencer.instructions import Pattern
from core.session.shot import DigitalTimeLane
from core.types.expression import Expression


def test_0():
    lane = DigitalTimeLane([(True, 1), (False, 1)])
    lane_compiler = DigitalLaneCompiler(
        lane, ["a", "b"], [Expression("1 s"), Expression("1 s")]
    )
    result = lane_compiler.compile(VariableNamespace(), 1)
    assert result == Pattern([True]) * 1_000_000_000 + Pattern([False]) * 1_000_000_000


def test_1():
    lane = DigitalTimeLane([(Expression("a"), 1), (Expression("b"), 1)])
    lane_compiler = DigitalLaneCompiler(
        lane, ["a", "b"], [Expression("1 s"), Expression("1 s")]
    )
    result = lane_compiler.compile(VariableNamespace({"a": True, "b": False}), 1)

    assert result == Pattern([True]) * 1_000_000_000 + Pattern([False]) * 1_000_000_000


def test_2():
    lane = DigitalTimeLane([(True, 2), (False, 1)])
    lane_compiler = DigitalLaneCompiler(lane, ["a", "b", "c"], [Expression("1 s")] * 3)
    result = lane_compiler.compile(VariableNamespace(), 1)
    assert (
        result == Pattern([True]) * 2_000_000_000 + Pattern([False]) * 1_000_000_000
    ), str(result)
