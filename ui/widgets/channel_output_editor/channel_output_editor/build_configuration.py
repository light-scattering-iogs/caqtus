import functools

from core.device.sequencer.configuration import ChannelOutput, LaneValues
from .functional_blocks import FunctionalBlock, TimeLaneBlock


@functools.singledispatch
def build_output(block: FunctionalBlock) -> ChannelOutput:
    """Builds the channel output configuration from the given block."""

    raise NotImplementedError(f"<build_output> not implemented for {type(block)}")


@build_output.register
def build_lane_output(block: TimeLaneBlock) -> LaneValues:
    return LaneValues(lane=block.get_lane_name(), default=block.get_default_value())


class OutputConstructionError(ValueError):
    pass


class MissingInputError(OutputConstructionError):
    pass
