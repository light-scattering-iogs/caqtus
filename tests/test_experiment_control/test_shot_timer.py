import pytest
import trio.testing

from caqtus.experiment_control.sequence_execution import ShotTimer


def test_elapsed():
    async def main():
        timer = ShotTimer._create()
        assert timer.elapsed() == pytest.approx(0, abs=1e-3)
        await trio.sleep(1)
        assert timer.elapsed() == pytest.approx(1, rel=1e-3)

    trio.run(main, clock=trio.testing.MockClock(autojump_threshold=0))


def test_positive_wait():
    async def main():
        timer = ShotTimer._create()
        duration = await timer.wait_until(1)
        assert duration == pytest.approx(1, rel=1e-3)
        assert timer.elapsed() == pytest.approx(1, rel=1e-3)

    trio.run(main, clock=trio.testing.MockClock(autojump_threshold=0))


def test_negative_wait():
    async def main():
        timer = ShotTimer._create()
        await trio.sleep(1)
        duration = await timer.wait_until(0.5)
        assert duration == pytest.approx(-0.5, rel=1e-3)
        assert timer.elapsed() == pytest.approx(1, rel=1e-3)

    trio.run(main, clock=trio.testing.MockClock(autojump_threshold=0))


def test_negative_target():
    async def main():
        timer = ShotTimer._create()
        with pytest.raises(ValueError):
            await timer.wait_until(-1)

    trio.run(main, clock=trio.testing.MockClock(autojump_threshold=0))
