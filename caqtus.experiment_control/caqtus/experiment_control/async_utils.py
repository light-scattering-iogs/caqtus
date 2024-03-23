"""This module provides utilities functions to run shot on the experiment
asynchronously.

These functions can manipulate :class:`caqtus.device.Device` objects.
However, the interface of the devices are typically synchronous: the methods that a
device provides are blocking.
This means that by default, it is only possible to talk to one device at a time.
To talk to multiple devices concurrently, we need to use asynchronous programming.

The functions in this module use structured concurrency with the async/await syntax for
this.
"""

import contextlib
from collections.abc import AsyncGenerator, AsyncIterable, Iterable, AsyncIterator
from typing import Protocol, TypeVar

import anyio
import anyio.to_thread

from caqtus.device.camera import Camera
from caqtus.types.image import Image


class SequencedDevice(Protocol):
    """A device that can be sequenced."""

    def start_sequence(self) -> None:
        """Starts the sequence on the device."""

        ...


async def engage_sequenced_device(device: SequencedDevice):
    """Starts the sequence on the given device asynchronously."""

    await anyio.to_thread.run_sync(device.start_sequence)


@contextlib.asynccontextmanager
async def engage_camera_acquisition(
    camera: Camera, exposures: list[float]
) -> AsyncGenerator[AsyncIterable[Image], None]:
    async with async_context_manager(camera.acquire(exposures)) as images:
        yield async_iterable(images)


T = TypeVar("T")


@contextlib.asynccontextmanager
async def async_context_manager(
    cm: contextlib.AbstractContextManager[T],
) -> AsyncGenerator[T, None]:
    """Transform a sync context manager in an async context manager.

    The __enter__ and __exit__ methods of the context manager will be executed in
    another thread.
    """

    entered = await anyio.to_thread.run_sync(cm.__enter__)
    try:
        yield entered
    except BaseException as exc:
        cm.__exit__(type(exc), exc, exc.__traceback__)
        raise
    else:
        await anyio.to_thread.run_sync(cm.__exit__, None, None, None)


@contextlib.asynccontextmanager
async def enter_context_group(
    *cms: contextlib.AbstractAsyncContextManager[T],
) -> AsyncGenerator[list[T], None]:
    result: dict[int, T] = {}

    async def enter(i):
        result[i] = await stack.enter_async_context(cms[i])

    async with contextlib.AsyncExitStack() as stack:
        async with anyio.create_task_group() as tg:
            for i in range(len(cms)):
                tg.start_soon(enter, i)
        yield [result[i] for i in range(len(cms))]


async def async_iterable(iterable: Iterable[T]) -> AsyncIterable[T]:
    iterator = iter(iterable)
    done = object()
    while (value := await anyio.to_thread.run_sync(next, iterator, done)) is not done:
        yield value  # type: ignore


async def aenumerate(iterable: AsyncIterable[T]) -> AsyncIterator[tuple[int, T]]:
    counter = 0
    async for value in iterable:
        yield counter, value
        counter += 1
