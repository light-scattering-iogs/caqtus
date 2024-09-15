import contextlib
from collections.abc import AsyncGenerator, Generator
from typing import Protocol


class Closeable(Protocol):
    def close(self): ...


@contextlib.contextmanager
def close_on_error[R: Closeable](resource: R) -> Generator[R, None, None]:
    """Context manager that closes a resource if an error occurs.

    Beware that the resource will NOT be closed if the context manager is exited
    without an exception.
    """

    try:
        yield resource
    except:
        resource.close()
        raise


class AsyncCloseable(Protocol):
    async def aclose(self): ...


@contextlib.asynccontextmanager
async def aclose_on_error[R: AsyncCloseable](resource: R) -> AsyncGenerator[R, None]:
    """Async context manager that closes a resource if an error occurs.

    Beware that the resource will NOT be closed if the context manager is exited
    without an exception.
    """

    try:
        yield resource
    except:
        await resource.aclose()
        raise
