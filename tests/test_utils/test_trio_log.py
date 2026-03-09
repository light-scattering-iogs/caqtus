import logging

import anyio.lowlevel
import trio
import trio.testing

from caqtus.utils._trio_instrumentation import LogBlockingTaskInstrument


def test_running_long_task_emits_warning(caplog):
    logger = logging.getLogger(test_running_long_task_emits_warning.__name__)
    instrument = LogBlockingTaskInstrument(0.1, logger)

    clock = trio.testing.MockClock()

    async def main():
        # Simulate a task that doesn't yield back to the event loop for a long time.
        # This task also never awaits
        clock.jump(0.2)

    with caplog.at_level(logging.WARNING, logger=logger.name):
        trio.run(main, instruments=[instrument], clock=clock)
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.WARNING
    task = record.args[0]
    assert isinstance(task, trio.lowlevel.Task)
    assert task.name == f"{__name__}.{main.__qualname__}"


def test_running_short_task_does_not_emit_warning(caplog):
    logger = logging.getLogger(test_running_short_task_does_not_emit_warning.__name__)
    instrument = LogBlockingTaskInstrument(0.1, logger)

    clock = trio.testing.MockClock()

    async def main():
        # Simulate a task that yields back to the event loop quickly
        clock.jump(0.05)
        await anyio.lowlevel.checkpoint()

    with caplog.at_level(logging.WARNING, logger=logger.name):
        trio.run(main, instruments=[instrument], clock=clock)
    assert not caplog.records
