from caqtus.device.sequencer.channel_commands import LaneValues
from caqtus.device.sequencer.channel_commands.logic import NotGate
from caqtus.device.sequencer.timing import to_time_step
from caqtus.shot_compilation import SequenceContext, ShotContext
from caqtus.shot_compilation.lane_compilation import DimensionedSeries
from caqtus.shot_compilation.timed_instructions import Pattern
from caqtus.types.expression import Expression
from caqtus.types.iteration import StepsConfiguration
from caqtus.types.parameter import ParameterNamespace
from caqtus.types.timelane import DigitalTimeLane, TimeLanes
from caqtus.types.units import dimensionless


def test_not_gate_invert_input():
    input_ = LaneValues("Test lane")
    not_gate = NotGate(input_)

    time_step = to_time_step(1)
    shot_context = ShotContext(
        SequenceContext._new(
            {},
            StepsConfiguration.empty(),
            ParameterNamespace.empty(),
            TimeLanes(
                ["step 0", "step 1"],
                [Expression("1 s"), Expression("1 s")],
                {"Test lane": DigitalTimeLane([True, False])},
            ),
        ),
        {},
        {},
    )
    evaluated_not_gate = not_gate.evaluate(time_step, 0, 0, shot_context)
    assert evaluated_not_gate == DimensionedSeries(
        values=(1_000_000_000 * Pattern([False]) + 1_000_000_000 * Pattern([True])),
        units=dimensionless,
    )
