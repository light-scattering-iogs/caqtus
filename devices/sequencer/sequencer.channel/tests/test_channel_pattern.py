from hypothesis import given
from hypothesis.strategies import composite, integers, lists

from sequencer.channel import ChannelPattern


@composite
def channel_pattern(draw, length: int):
    return ChannelPattern(draw(lists(integers(), min_size=length, max_size=length)))


@given(channel_pattern(length=10))
def test_channel_pattern(pattern: ChannelPattern):
    assert len(pattern) == 10
