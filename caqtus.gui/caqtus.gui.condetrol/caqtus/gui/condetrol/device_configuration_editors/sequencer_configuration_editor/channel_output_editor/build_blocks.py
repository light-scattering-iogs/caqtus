import functools

from caqtus.device.sequencer.configuration import (
    ChannelConfiguration,
    ChannelOutput,
    LaneValues,
    CalibratedAnalogMapping,
    Constant,
    DeviceTrigger,
    Advance,
    Delay,
)
from .connection import ConnectionLink
from .functional_blocks import (
    FunctionalBlock,
    ChannelOutputBlock,
    TimeLaneBlock,
    AnalogMappingBlock,
    HoldBlock,
    DeviceTriggerBlock,
    AdvanceBlock,
    DelayBlock,
)


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
    link.connect()
    return block


@functools.singledispatch
def build_block(channel_output: ChannelOutput) -> FunctionalBlock:
    """Builds a block that represents the given channel output.

    This function is the inverse of `build_output`.
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
def build_lane_block(channel_output: LaneValues) -> TimeLaneBlock:
    block = TimeLaneBlock()
    block.set_lane_name(channel_output.lane)
    block.set_default_value(channel_output.default)
    return block


@build_block.register
def build_hold_block(channel_output: Constant) -> HoldBlock:
    block = HoldBlock()
    block.set_value(channel_output.value)
    return block


@build_block.register
def build_device_trigger_block(
    channel_output: DeviceTrigger,
) -> DeviceTriggerBlock:
    block = DeviceTriggerBlock()
    block.set_device_name(channel_output.device_name)
    return block


@build_block.register
def build_analog_mapping_block(
    channel_output: CalibratedAnalogMapping,
) -> AnalogMappingBlock:
    block = AnalogMappingBlock()
    measured_values = channel_output.measured_data_points
    block.set_data_points(
        [x for x, _ in measured_values], [y for _, y in measured_values]
    )
    block.set_input_units(channel_output.input_units)
    block.set_output_units(channel_output.output_units)
    previous_block = build_block(channel_output.input_)
    link = ConnectionLink(
        input_connection=block.input_connections[0],
        output_connection=previous_block.output_connection,
    )
    link.connect()
    return block


@build_block.register
def build_advance_block(channel_output: Advance) -> AdvanceBlock:
    block = AdvanceBlock()
    block.set_advance(channel_output.advance)
    previous_block = build_block(channel_output.input_)
    link = ConnectionLink(
        input_connection=block.input_connections[0],
        output_connection=previous_block.output_connection,
    )
    link.connect()
    return block


@build_block.register
def build_delay_block(channel_output: Delay) -> DelayBlock:
    block = DelayBlock()
    block.set_delay(channel_output.delay)
    previous_block = build_block(channel_output.input_)
    link = ConnectionLink(
        input_connection=block.input_connections[0],
        output_connection=previous_block.output_connection,
    )
    link.connect()
    return block
