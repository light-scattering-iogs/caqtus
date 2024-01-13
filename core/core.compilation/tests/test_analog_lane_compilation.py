import numpy as np

from core.compilation import VariableNamespace
from core.compilation.lane_compilers import AnalogLaneCompiler
from core.device.sequencer.instructions import Pattern
from core.session.shot.timelane import AnalogTimeLane
from core.types.expression import Expression


def test_0():
    lane = AnalogTimeLane([(Expression("0 dB"), 1), (Expression("10 dB"), 1)])
    compiler = AnalogLaneCompiler(lane, ["step1", "step2"], [Expression("10 ns")] * 2)
    result = compiler.compile(VariableNamespace(), 1)
    expected = Pattern([1.0]) * 10 + Pattern([10.0]) * 10
    assert np.allclose(result.to_pattern().array, expected.to_pattern().array), str(
        result
    )
