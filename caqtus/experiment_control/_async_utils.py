import contextlib

import anyio


@contextlib.contextmanager
def renamed_exception_group(message: str):
    try:
        yield
    except ExceptionGroup as e:
        raise ExceptionGroup(message, e.exceptions) from None


@contextlib.asynccontextmanager
async def create_task_group_with_message(message: str):
    with renamed_exception_group(message):
        async with anyio.create_task_group() as tg:
            yield tg