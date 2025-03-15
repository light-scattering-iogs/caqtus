import datetime
import logging
from typing import Mapping

import numpy as np
import polars as pl
import pytest

from caqtus.device import DeviceName, DeviceConfiguration
from caqtus.extension import Experiment
from caqtus.session import StorageManager, PureSequencePath
from caqtus.session._shot_id import ShotId
from caqtus.types.data import DataLabel, DataType, ImageType
from caqtus.types.expression import Expression
from caqtus.types.image import Width, Height, ImageLabel
from caqtus.types.image.roi import RectangularROI
from caqtus.types.iteration import StepsConfiguration, LinspaceLoop, ExecuteShot
from caqtus.types.parameter import ParameterNamespace, ParameterSchema
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
        lanes={
            "Camera": CameraTimeLane(
                [None, TakePicture(ImageLabel(DataLabel("picture 1"))), None]
            )
        },
    )


class MockCamera(DeviceConfiguration):
    def get_data_schema(
        self, parameter_schema: ParameterSchema, time_lanes: TimeLanes
    ) -> Mapping[DataLabel, DataType]:
        return {
            DataLabel("picture 1"): ImageType(
                pl.UInt32(),
                RectangularROI((Width(100), Height(100)), 0, 100, 0, 100),
            )
        }

    @classmethod
    def load(cls, data) -> "MockCamera":
        return cls(data["remote_server"])

    def dump(self) -> dict:
        return {"remote_server": self.remote_server}


@pytest.fixture
def session_maker(initialized_database_config) -> StorageManager:
    exp = Experiment(initialized_database_config)
    exp.setup_default_extensions()
    exp._extension.device_configurations_serializer.register_device_configuration(
        MockCamera, MockCamera.dump, MockCamera.load
    )
    return exp._get_storage_manager(check_schema=False)


@pytest.fixture
def done_sequence(session_maker: StorageManager):
    path = PureSequencePath(r"\test")
    with session_maker.session() as session:
        session.sequences.create(path, steps_configuration(), time_lanes())
        session.sequences.set_preparing(
            path,
            {DeviceName("Camera"): MockCamera(remote_server=None)},
            ParameterNamespace.empty(),
        )
        session.sequences.set_running(path, start_time="now")
        for shot_id in range(10):
            session.sequences.create_shot(
                ShotId(path, shot_id),
                shot_parameters={DottedVariableName("exposure"): shot_id * Unit("ms")},
                shot_data={
                    DataLabel("Camera\\picture 1"): np.full(
                        (100, 100), shot_id, dtype=np.uint32
                    )
                },
                shot_start_time=datetime.datetime.now(),
                shot_end_time=datetime.datetime.now(),
            )
        session.sequences.set_finished(path, stop_time="now")
    yield path
    with session_maker.session() as session:
        session.paths.delete_path(path, delete_sequences=True)


def test_saved_pictures_can_be_retrieved(done_sequence, session_maker: StorageManager):
    logging.basicConfig(level=logging.DEBUG)
    with session_maker.session() as session:
        sequence = session.get_sequence(done_sequence)
        schema = sequence.lazy_load().collect_schema()
        assert schema == pl.Schema(
            {
                "sequence": pl.Categorical(ordering="lexical"),
                "shot_index": pl.UInt64(),
                "shot_start_time": pl.Datetime(time_unit="ms", time_zone="UTC"),
                "shot_end_time": pl.Datetime(time_unit="ms", time_zone="UTC"),
                "exposure": pl.Float64(),
                "Camera\\picture 1": pl.Array(pl.UInt32, shape=(100, 100)),
            }
        )
        assert len(sequence.lazy_load().collect()) == 10
