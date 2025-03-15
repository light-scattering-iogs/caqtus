import datetime

import pytest

from caqtus.session import StorageManager, PureSequencePath
from caqtus.session._shot_id import ShotId
from caqtus.types.expression import Expression
from caqtus.types.iteration import StepsConfiguration, LinspaceLoop, ExecuteShot
from caqtus.types.parameter import ParameterNamespace
from caqtus.types.timelane import TimeLanes, CameraTimeLane, TakePicture
from caqtus.types.units import Unit
from caqtus.types.variable_name import DottedVariableName


def steps_configuration() -> StepsConfiguration:
    step_configuration = StepsConfiguration(
        steps=[
            LinspaceLoop(
                variable=DottedVariableName("exposure"),
                start=Expression("0 ms"),
                stop=Expression("10 ms"),
                num=10,
                sub_steps=[
                    ExecuteShot(),
                ],
            )
        ]
    )
    return step_configuration


def time_lanes() -> TimeLanes:
    return TimeLanes(
        step_names=["start", "picture", "stop"],
        step_durations=[Expression("1 ms"), Expression("exposure"), Expression("2 ms")],
        lanes={"Camera": CameraTimeLane([None, TakePicture("picture 1"), None])},
    )


@pytest.fixture
def done_sequence(session_maker: StorageManager):
    path = PureSequencePath(r"\test")
    with session_maker.session() as session:
        session.sequences.create(path, steps_configuration(), time_lanes())
        session.sequences.set_preparing(path, {}, ParameterNamespace.empty())
        session.sequences.set_running(path, start_time="now")
        for shot_id in range(10):
            session.sequences.create_shot(
                ShotId(path, shot_id),
                shot_parameters={DottedVariableName("exposure"): shot_id * Unit("ms")},
                shot_data={},
                shot_start_time=datetime.datetime.now(),
                shot_end_time=datetime.datetime.now(),
            )
        session.sequences.set_finished(path, stop_time="now")
    yield path
    with session_maker.session() as session:
        session.paths.delete_path(path, delete_sequences=True)


def test_loading_data(done_sequence, session_maker: StorageManager):
    with session_maker.session() as session:
        sequence = session.get_sequence(done_sequence)
        df = sequence.lazy_load().collect()
        assert len(df) == 10
