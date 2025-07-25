import logging
import warnings

import anyio.lowlevel
import pytest
import trio
import trio.testing

from caqtus.utils._trio_instrumentation import (
    LogBlockingTaskInstrument,
    TaskDurationWarning,
)


def test_running_long_task_emits_warning():
    instrument = LogBlockingTaskInstrument(0.1)

    clock = trio.testing.MockClock()

    async def main():
        # Simulate a task that doesn't yield back to the event loop for a long time.
        # This task also never awaits
        clock.jump(0.2)

    with pytest.warns(TaskDurationWarning) as records:
        trio.run(main, instruments=[instrument], clock=clock)
    assert len(records) == 1


def test_running_short_task_does_not_emit_warning():
    instrument = LogBlockingTaskInstrument(0.1)

    clock = trio.testing.MockClock()

    async def main():
        # Simulate a task that yields back to the event loop quickly
        clock.jump(0.05)
        await anyio.lowlevel.checkpoint()

    with warnings.catch_warnings(record=True) as records:
        trio.run(main, instruments=[instrument], clock=clock)
    assert not records
