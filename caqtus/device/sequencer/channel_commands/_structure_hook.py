from caqtus.utils import serialization
from ._channel_sources import LaneValues, Constant
from caqtus.device.sequencer.channel_commands.channel_output import ChannelOutput


def structure_channel_output(data, _):
    # This is a legacy workaround for structuring ChannelOutput subclasses.
    # This is because at the beginning of the project, the type field was not serialized
    # but instead the type was inferred from the structure of the data.
    # For new data, we can use the type field to determine the type of the
    # ChannelOutput subclass, but for old data, we need to infer the type from the
    # fields present in the data.
    if "type" in data:
        return serialization.structure(data, ChannelOutput)
    elif "lane" in data:
        return serialization.structure(data, LaneValues)
    elif data.keys() == {"value"}:
        return serialization.structure(data, Constant)
    else:
        raise ValueError(f"Cannot structure {data} as a ChannelOutput")
