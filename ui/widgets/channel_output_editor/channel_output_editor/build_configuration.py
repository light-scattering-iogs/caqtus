import functools

from core.device.sequencer.configuration import (
    ChannelOutput,
    LaneValues,
    CalibratedAnalogMapping,
)
from .functional_blocks import FunctionalBlock, TimeLaneBlock, AnalogMappingBlock


@functools.singledispatch
def build_output(block: FunctionalBlock) -> ChannelOutput:
    """Builds the channel output configuration from the given block.

    This function is the inverse of `create_functional_blocks`.
    It is used to convert the blocks in the scene to a channel output configuration.
    When called on a given block, it returns a ChannelOutput object that represents
    output pipeline of the block, including all its input connections.
    """

    raise NotImplementedError(f"<build_output> not implemented for {type(block)}")


@build_output.register
def build_lane_output(block: TimeLaneBlock) -> LaneValues:
    return LaneValues(lane=block.get_lane_name(), default=block.get_default_value())


@build_output.register
def build_analog_mapping_output(block: AnalogMappingBlock) -> CalibratedAnalogMapping:
    link = block.input_connections[0].link
    if link is None:
        raise MissingInputError("Analog mapping block has no input")

    input_block = link.output_connection.block
    x_points, y_points = block.get_data_points()
    return CalibratedAnalogMapping(
        input_=build_output(input_block),
        measured_data_points=tuple((x, y) for x, y in zip(x_points, y_points)),
        input_units=block.get_input_units(),
        output_units=block.get_output_units(),
    )


class OutputConstructionError(ValueError):
    pass


class MissingInputError(OutputConstructionError):
    pass
