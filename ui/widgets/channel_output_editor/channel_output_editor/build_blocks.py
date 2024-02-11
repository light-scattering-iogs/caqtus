import functools

from core.device.sequencer.configuration import (
    ChannelConfiguration,
    ChannelOutput,
    LaneValues,
)
from .connection import ConnectionLink
from .functional_blocks import FunctionalBlock, ChannelOutputBlock, TimeLaneBlock


def create_functional_blocks(
    channel_label: str,
    channel_configuration: ChannelConfiguration,
) -> ChannelOutputBlock:
    """Creates the functional blocks that represent the channel output pipeline.

    Returns:
        A single channel output block that represents the output of the channel.
        All blocks can be accessed by walking the input connections of the output block.
    """

    block = ChannelOutputBlock(channel_label, channel_configuration.description)
    previous_block = build_block(channel_configuration.output)

    output_connection = previous_block.output_connection
    assert output_connection is not None

    link = ConnectionLink(
        input_connection=block.input_connections[0],
        output_connection=output_connection,
    )
    block.input_connections[0].link = link
    output_connection.link = link
    return block


@functools.singledispatch
def build_block(channel_output: ChannelOutput) -> FunctionalBlock:
    """Builds a block that represents the given channel output.

    The returned block has its input linked to the previous blocks and its output not
    linked to anything.
    All functional blocks and links accessible from the returned block have no parent
    item.
    All blocks and links must still be added to a scene.
    """

    raise NotImplementedError(
        f"<build_block> not implemented for {type(channel_output)}"
    )


@build_block.register
def build_lane_block(channel_output: LaneValues) -> FunctionalBlock:
    block = TimeLaneBlock()
    block.set_lane_name(channel_output.lane)
    return block
