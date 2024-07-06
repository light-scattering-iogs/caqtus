import contextlib
from typing import Protocol


class Closeable(Protocol):
    def close(self): ...


@contextlib.contextmanager
def close_on_error[R: Closeable](resource: R) -> R:
    """Context manager that closes a resource if an error occurs.

    Beware that the resource will NOT be closed if the context manager is exited
    without an exception.
    """

    try:
        yield R
    except:
        resource.close()
        raise


class AsyncCloseable(Protocol):
    async def aclose(self): ...


@contextlib.asynccontextmanager
async def aclose_on_error[R: AsyncCloseable](resource: R) -> R:
    """Async context manager that closes a resource if an error occurs.

    Beware that the resource will NOT be closed if the context manager is exited
    without an exception.
    """

    try:
        yield
    except:
        await resource.aclose()
        raise
