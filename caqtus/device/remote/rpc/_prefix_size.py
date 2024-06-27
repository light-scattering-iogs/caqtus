from anyio.abc import AnyByteSendStream
from anyio.streams.buffered import BufferedByteReceiveStream, AnyByteReceiveStream


async def receive_with_size_prefix(stream: AnyByteReceiveStream) -> bytes:
    """Receive a message with the data size prefixed in the stream."""

    buffered_stream = BufferedByteReceiveStream(stream)
    length_bytes = await buffered_stream.receive_exactly(8)
    length = int.from_bytes(length_bytes, "big")
    data = await buffered_stream.receive_exactly(length)
    return data


async def send_with_size_prefix(stream: AnyByteSendStream, data: bytes):
    """Send a message with the data size prefixed in the stream."""

    length_bytes = len(data).to_bytes(8, "big")
    await stream.send(length_bytes)
    await stream.send(data)
