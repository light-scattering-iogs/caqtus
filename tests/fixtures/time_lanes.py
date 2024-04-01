import pytest

from caqtus.session.shot import TimeLanes
from caqtus.types.expression import Expression


@pytest.fixture
def time_lanes() -> TimeLanes:
    return TimeLanes(
        step_names=["step1", "step2"],
        step_durations=[Expression("1 ms"), Expression("2 ms")],
        lanes={},
    )
