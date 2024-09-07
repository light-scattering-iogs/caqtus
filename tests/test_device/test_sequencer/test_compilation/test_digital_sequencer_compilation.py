from typing import Type

import pytest

from caqtus.device import DeviceName
from caqtus.device.sequencer import (
    SequencerConfiguration,
    DigitalChannelConfiguration,
    SequencerCompiler,
    ChannelConfiguration,
)
from caqtus.device.sequencer.channel_commands import LaneValues, Constant
from caqtus.device.sequencer.instructions import Pattern
from caqtus.device.sequencer.timing import to_time_step
from caqtus.device.sequencer.trigger import SoftwareTrigger
from caqtus.shot_compilation.compilation_contexts import SequenceContext, ShotContext
from caqtus.types.expression import Expression
from caqtus.types.timelane import TimeLanes, DigitalTimeLane


class MockSequencerConfiguration(SequencerConfiguration):
    def channel_types(self) -> tuple[Type[ChannelConfiguration], ...]:
        return DigitalChannelConfiguration, DigitalChannelConfiguration


@pytest.fixture
def sequencer_config() -> SequencerConfiguration:
    return MockSequencerConfiguration(
        remote_server=None,
        time_step=to_time_step(10),
        trigger=SoftwareTrigger(),
        channels=(
            DigitalChannelConfiguration(
                description="Channel 0", output=LaneValues("test")
            ),
            DigitalChannelConfiguration(
                description="Channel 1",
                output=LaneValues("test 1", default=Constant(Expression("False"))),
            ),
        ),
    )


def test_single_digital_lane(sequencer_config):
    time_lanes = TimeLanes(
        step_names=["step 0", "yo"],
        step_durations=[Expression("10 ms"), Expression("20 ms")],
        lanes={"test": DigitalTimeLane([True, False])},
    )
    sequence_context = SequenceContext(
        {DeviceName("sequencer"): sequencer_config}, time_lanes
    )

    shot_context = ShotContext(sequence_context, {}, {})
    compiler = SequencerCompiler(
        DeviceName("sequencer"), shot_context._sequence_context
    )
    result = compiler.compile_shot_parameters(shot_context)
    sequence = result["sequence"]
    assert (
        sequence["ch 0"] == Pattern([True]) * 1_000_000 + Pattern([False]) * 2_000_000
    )


def test_multiple_digital_lane(sequencer_config):
    time_lanes = TimeLanes(
        step_names=["step 0", "step 1", "step 2"],
        step_durations=[Expression("10 ms"), Expression("20 ms"), Expression("10 ms")],
        lanes={
            "test": DigitalTimeLane([True, True, False]),
            "test 1": DigitalTimeLane([False, True, True]),
        },
    )
    sequence_context = SequenceContext(
        {DeviceName("sequencer"): sequencer_config}, time_lanes
    )

    shot_context = ShotContext(sequence_context, {}, {})
    compiler = SequencerCompiler(
        DeviceName("sequencer"), shot_context._sequence_context
    )
    result = compiler.compile_shot_parameters(shot_context)
    sequence = result["sequence"]
    assert (
        sequence["ch 0"]
        == Pattern([True]) * 1_000_000
        + Pattern([True]) * 2_000_000
        + Pattern([False]) * 1_000_000
    )
    assert (
        sequence["ch 1"]
        == Pattern([False]) * 1_000_000
        + Pattern([True]) * 2_000_000
        + Pattern([True]) * 1_000_000
    )
