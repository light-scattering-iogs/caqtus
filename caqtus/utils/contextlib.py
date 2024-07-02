import contextlib
from typing import Protocol


class Closeable(Protocol):
    def close(self): ...


@contextlib.contextmanager
def close_on_error(resource: Closeable):
    """Context manager that closes a resource if an error occurs.

    Beware that the resource will NOT be closed if the context manager is exited
    without an exception.
    """

    try:
        yield
    except:
        resource.close()
        raise
