import pickle

import anyio.to_process
import pytest
import trio

from caqtus.utils._tblib import ensure_exception_pickling


class CustomException(Exception):
    pass


@ensure_exception_pickling
def f():
    raise RuntimeError("An error occurred") from CustomException(
        "A custom error occurred"
    )


def test_custom_exception_pickling():
    try:
        f()
    except RuntimeError as exc:
        exception = exc

    dumped = pickle.dumps(exception)
    loaded = pickle.loads(dumped)
    assert isinstance(loaded.__cause__, CustomException)


@pytest.fixture
def anyio_backend():
    return "trio"


async def test_subprocess_exception_pickling(anyio_backend):
    try:
        await anyio.to_process.run_sync(f)
    except RuntimeError as exc:
        assert isinstance(exc.__cause__, CustomException)


def test_trio_cancelled_exception_pickling():
    exc = trio.Cancelled._create()
    dumped = pickle.dumps(exc)
    loaded = pickle.loads(dumped)
    assert isinstance(loaded, trio.Cancelled)
