from anyio.abc import ByteSendStream
from anyio.streams.buffered import BufferedByteReceiveStream


async def receive_with_size_prefix(stream: BufferedByteReceiveStream) -> bytes:
    size = await stream.receive_exactly(8)
    size = int.from_bytes(size, "big")
    return await stream.receive_exactly(size)


async def send_with_size_prefix(stream: ByteSendStream, data: bytes) -> None:
    size = len(data).to_bytes(8, "big")
    await stream.send(size + data)
