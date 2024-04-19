from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Optional

import attrs
import numpy as np
import sqlalchemy.orm
from returns.result import Result
from returns.result import Success, Failure
from sqlalchemy import func, select

from caqtus.device import DeviceConfiguration, DeviceName
from caqtus.types.data import DataLabel, Data, is_data
from caqtus.types.expression import Expression
from caqtus.types.parameter import Parameter
from caqtus.types.units import Quantity
from caqtus.types.variable_name import DottedVariableName
from caqtus.utils import serialization
from ._path_table import SQLSequencePath
from ._sequence_table import (
    SQLSequence,
    SQLIterationConfiguration,
    SQLTimelanes,
    SQLDeviceConfiguration,
    SQLSequenceParameters,
)
from ._serializer import Serializer
from ._shot_tables import SQLShot, SQLShotParameter, SQLShotArray, SQLStructuredShotData
from .._return_or_raise import unwrap
from ..parameter_namespace import ParameterNamespace
from ..path import PureSequencePath, BoundSequencePath
from ..path_hierarchy import PathNotFoundError, PathHasChildrenError
from ..sequence import Sequence, Shot
from ..sequence.iteration_configuration import (
    IterationConfiguration,
)
from ..sequence.state import State
from ..sequence_collection import (
    PathIsSequenceError,
    PathIsNotSequenceError,
    InvalidStateTransitionError,
    SequenceNotEditableError,
    SequenceStats,
    ShotNotFoundError,
)
from ..sequence_collection import SequenceCollection
from ..shot import TimeLanes

if TYPE_CHECKING:
    from ._experiment_session import SQLExperimentSession


@attrs.frozen
class SQLSequenceCollection(SequenceCollection):
    parent_session: "SQLExperimentSession"
    serializer: Serializer

    def __getitem__(self, item: str) -> Sequence:
        return Sequence(BoundSequencePath(item, self.parent_session))

    def is_sequence(self, path: PureSequencePath) -> Result[bool, PathNotFoundError]:
        if path.is_root():
            return Success(False)
        return self._query_path_model(path).map(
            lambda path_model: bool(path_model.sequence)
        )

    def get_contained_sequences(self, path: PureSequencePath) -> list[PureSequencePath]:
        if unwrap(self.is_sequence(path)):
            return [path]

        path_hierarchy = self.parent_session.paths
        result = []
        for child in unwrap(path_hierarchy.get_children(path)):
            result += self.get_contained_sequences(child)
        return result

    def set_global_parameters(
        self, path: PureSequencePath, parameters: ParameterNamespace
    ) -> None:
        sequence = unwrap(self._query_sequence_model(path))
        if sequence.state != State.PREPARING:
            raise SequenceNotEditableError(path)

        if not isinstance(parameters, ParameterNamespace):
            raise TypeError(
                f"Invalid parameters type {type(parameters)}, "
                f"expected ParameterNamespace"
            )

        parameters_content = serialization.converters["json"].unstructure(
            parameters, ParameterNamespace
        )

        sequence.parameters.content = parameters_content

    def get_global_parameters(self, path: PureSequencePath) -> ParameterNamespace:
        sequence = unwrap(self._query_sequence_model(path))

        if sequence.state == State.DRAFT:
            raise RuntimeError("Sequence has not been prepared yet")

        parameters_content = sequence.parameters.content

        return serialization.converters["json"].structure(
            parameters_content, ParameterNamespace
        )

    def get_iteration_configuration(
        self, sequence: PureSequencePath
    ) -> IterationConfiguration:
        sequence_model = unwrap(self._query_sequence_model(sequence))
        return self.serializer.construct_sequence_iteration(
            sequence_model.iteration.content,
        )

    def set_iteration_configuration(
        self, sequence: Sequence, iteration_configuration: IterationConfiguration
    ) -> None:
        sequence_model = unwrap(self._query_sequence_model(sequence.path))
        if not sequence_model.state.is_editable():
            raise SequenceNotEditableError(sequence.path)
        iteration_content = self.serializer.dump_sequence_iteration(
            iteration_configuration
        )
        sequence_model.iteration.content = iteration_content
        sequence_model.expected_number_of_shots = (
            iteration_configuration.expected_number_shots()
        )

    def create(
        self,
        path: PureSequencePath,
        iteration_configuration: IterationConfiguration,
        time_lanes: TimeLanes,
    ) -> Sequence:
        self.parent_session.paths.create_path(path)
        if unwrap(self.is_sequence(path)):
            raise PathIsSequenceError(path)
        if unwrap(self.parent_session.paths.get_children(path)):
            raise PathHasChildrenError(path)

        iteration_content = self.serializer.dump_sequence_iteration(
            iteration_configuration
        )

        new_sequence = SQLSequence(
            path=unwrap(self._query_path_model(path)),
            parameters=SQLSequenceParameters(content=None),
            iteration=SQLIterationConfiguration(content=iteration_content),
            time_lanes=SQLTimelanes(content=self.serialize_time_lanes(time_lanes)),
            state=State.DRAFT,
            device_configurations=[],
            start_time=None,
            stop_time=None,
            expected_number_of_shots=iteration_configuration.expected_number_shots(),
        )
        self._get_sql_session().add(new_sequence)
        return Sequence(path)

    def serialize_time_lanes(self, time_lanes: TimeLanes) -> serialization.JSON:
        return dict(
            step_names=serialization.converters["json"].unstructure(
                time_lanes.step_names, list[str]
            ),
            step_durations=serialization.converters["json"].unstructure(
                time_lanes.step_durations, list[Expression]
            ),
            lanes={
                lane: self.serializer.dump_time_lane(time_lane)
                for lane, time_lane in time_lanes.lanes.items()
            },
        )

    def construct_time_lanes(self, time_lanes_content: serialization.JSON) -> TimeLanes:
        return TimeLanes(
            step_names=serialization.converters["json"].structure(
                time_lanes_content["step_names"], list[str]
            ),
            step_durations=serialization.converters["json"].structure(
                time_lanes_content["step_durations"], list[Expression]
            ),
            lanes={
                lane: self.serializer.construct_time_lane(time_lane_content)
                for lane, time_lane_content in time_lanes_content["lanes"].items()
            },
        )

    def get_time_lanes(self, sequence_path: PureSequencePath) -> TimeLanes:
        sequence_model = unwrap(self._query_sequence_model(sequence_path))
        return self.construct_time_lanes(sequence_model.time_lanes.content)

    def set_time_lanes(
        self, sequence_path: PureSequencePath, time_lanes: TimeLanes
    ) -> None:
        sequence_model = unwrap(self._query_sequence_model(sequence_path))
        if not sequence_model.state.is_editable():
            raise SequenceNotEditableError(sequence_path)
        sequence_model.time_lanes.content = self.serialize_time_lanes(time_lanes)

    def get_state(
        self, path: PureSequencePath
    ) -> Result[State, PathNotFoundError | PathIsNotSequenceError]:
        result = self._query_sequence_model(path)
        return result.map(lambda sequence: sequence.state)

    def set_state(self, path: PureSequencePath, state: State) -> None:
        sequence = unwrap(self._query_sequence_model(path))
        if not State.is_transition_allowed(sequence.state, state):
            raise InvalidStateTransitionError(
                f"Sequence at {path} can't transition from {sequence.state} to {state}"
            )
        sequence.state = state
        if state == State.DRAFT:
            sequence.start_time = None
            sequence.stop_time = None
            sequence.parameters.content = None
            delete_device_configurations = sqlalchemy.delete(
                SQLDeviceConfiguration
            ).where(SQLDeviceConfiguration.sequence == sequence)
            self._get_sql_session().execute(delete_device_configurations)

            delete_shots = sqlalchemy.delete(SQLShot).where(
                SQLShot.sequence == sequence
            )
            self._get_sql_session().execute(delete_shots)
        elif state == State.RUNNING:
            sequence.start_time = datetime.datetime.now(
                tz=datetime.timezone.utc
            ).replace(tzinfo=None)
        elif state in (State.INTERRUPTED, State.CRASHED, State.FINISHED):
            sequence.stop_time = datetime.datetime.now(
                tz=datetime.timezone.utc
            ).replace(tzinfo=None)

    def set_device_configurations(
        self,
        path: PureSequencePath,
        device_configurations: Mapping[DeviceName, DeviceConfiguration],
    ) -> None:
        sequence = unwrap(self._query_sequence_model(path))
        if sequence.state != State.PREPARING:
            raise SequenceNotEditableError(path)
        sql_device_configs = []
        for order, (name, device_configuration) in enumerate(
            device_configurations.items()
        ):
            type_name, content = self.serializer.dump_device_configuration(
                device_configuration
            )
            sql_device_configs.append(
                SQLDeviceConfiguration(
                    name=name, device_type=type_name, content=content
                )
            )
        sequence.device_configurations = sql_device_configs

    def get_device_configurations(
        self, path: PureSequencePath
    ) -> dict[DeviceName, DeviceConfiguration]:
        sequence = unwrap(self._query_sequence_model(path))
        if sequence.state == State.DRAFT:
            raise RuntimeError("Sequence has not been prepared yet")

        device_configurations = {}

        for device_configuration in sequence.device_configurations:
            constructed = self.serializer.load_device_configuration(
                device_configuration.device_type, device_configuration.content
            )
            device_configurations[device_configuration.name] = constructed
        return device_configurations

    def get_stats(
        self, path: PureSequencePath
    ) -> Result[SequenceStats, PathNotFoundError | PathIsNotSequenceError]:
        result = self._query_sequence_model(path)

        def extract_stats(sequence: SQLSequence) -> SequenceStats:
            number_shot_query = select(func.count()).select_from(
                select(SQLShot).where(SQLShot.sequence == sequence).subquery()
            )
            number_shot_run = (
                self._get_sql_session().execute(number_shot_query).scalar_one()
            )
            return SequenceStats(
                state=sequence.state,
                start_time=(
                    sequence.start_time.replace(tzinfo=datetime.timezone.utc)
                    if sequence.start_time is not None
                    else None
                ),
                stop_time=(
                    sequence.stop_time.replace(tzinfo=datetime.timezone.utc)
                    if sequence.stop_time is not None
                    else None
                ),
                number_completed_shots=number_shot_run,
                expected_number_shots=sequence.expected_number_of_shots,
            )

        return result.map(extract_stats)

    def create_shot(
        self,
        path: PureSequencePath,
        shot_index: int,
        shot_parameters: Mapping[DottedVariableName, Parameter],
        shot_data: Mapping[DataLabel, Data],
        shot_start_time: datetime.datetime,
        shot_end_time: datetime.datetime,
    ) -> None:
        sequence = unwrap(self._query_sequence_model(path))
        if sequence.state != State.RUNNING:
            raise RuntimeError("Can't create shot in sequence that is not running")
        if shot_index < 0:
            raise ValueError("Shot index must be non-negative")
        if sequence.expected_number_of_shots is not None:
            if shot_index >= sequence.expected_number_of_shots:
                raise ValueError(
                    f"Shot index must be less than the expected number of shots "
                    f"({sequence.expected_number_of_shots})"
                )

        parameters = self.serialize_shot_parameters(shot_parameters)

        array_data, structured_data = self.serialize_data(shot_data)

        shot = SQLShot(
            sequence=sequence,
            index=shot_index,
            parameters=SQLShotParameter(content=parameters),
            array_data=array_data,
            structured_data=structured_data,
            start_time=shot_start_time.astimezone(datetime.timezone.utc).replace(
                tzinfo=None
            ),
            end_time=shot_end_time.astimezone(datetime.timezone.utc).replace(
                tzinfo=None
            ),
        )
        self._get_sql_session().add(shot)

    @staticmethod
    def serialize_data(
        data: Mapping[DataLabel, Data]
    ) -> tuple[list[SQLShotArray], list[SQLStructuredShotData]]:
        arrays = []
        structured_data = []
        for label, value in data.items():
            if not is_data(value):
                raise TypeError(f"Invalid data type for {label}: {type(value)}")
            if isinstance(value, np.ndarray):
                arrays.append(
                    SQLShotArray(
                        label=label,
                        dtype=str(value.dtype),
                        shape=value.shape,
                        bytes_=value.tobytes(),
                    )
                )
            else:
                structured_data.append(
                    SQLStructuredShotData(label=label, content=value)
                )
        return arrays, structured_data

    @staticmethod
    def serialize_shot_parameters(
        shot_parameters: Mapping[DottedVariableName, Parameter]
    ) -> dict[str, serialization.JSON]:
        return {
            str(variable_name): serialization.converters["json"].unstructure(
                parameter, Parameter
            )
            for variable_name, parameter in shot_parameters.items()
        }

    def get_shots(
        self, path: PureSequencePath
    ) -> Result[list[Shot], PathNotFoundError | PathIsNotSequenceError]:
        sql_sequence = self._query_sequence_model(path)

        def extract_shots(sql_sequence: SQLSequence) -> list[Shot]:
            sequence = Sequence(BoundSequencePath(path, self.parent_session))
            return [Shot(sequence, shot.index) for shot in sql_sequence.shots]

        return sql_sequence.map(extract_shots)

    def get_shot_parameters(
        self, path: PureSequencePath, shot_index: int
    ) -> Mapping[DottedVariableName, Parameter]:
        shot_model = unwrap(self._query_shot_model(path, shot_index))
        values = shot_model.parameters.content
        parameters = serialization.converters["json"].structure(
            values, dict[DottedVariableName, bool | int | float | Quantity]
        )
        return parameters

    def get_all_shot_data(
        self, path: PureSequencePath, shot_index: int
    ) -> dict[DataLabel, Data]:
        shot_model = unwrap(self._query_shot_model(path, shot_index))
        arrays = shot_model.array_data
        structured_data = shot_model.structured_data
        result = {}
        for array in arrays:
            result[array.label] = np.frombuffer(
                array.bytes_, dtype=array.dtype
            ).reshape(array.shape)
        for data in structured_data:
            result[data.label] = data.content
        return result

    def get_shot_data_by_label(
        self, path: PureSequencePath, shot_index: int, data_label: DataLabel
    ) -> Data:
        shot_model = unwrap(self._query_shot_model(path, shot_index))
        structure_query = select(SQLStructuredShotData).where(
            (SQLStructuredShotData.shot == shot_model)
            & (SQLStructuredShotData.label == data_label)
        )
        result = self._get_sql_session().execute(structure_query)
        if found := result.scalar():
            return found.content
        array_query = select(SQLShotArray).where(
            (SQLShotArray.shot == shot_model) & (SQLShotArray.label == data_label)
        )
        result = self._get_sql_session().execute(array_query)
        if found := result.scalar():
            return np.frombuffer(found.bytes_, dtype=found.dtype).reshape(found.shape)
        raise KeyError(f"Data <{data_label}> not found in shot {shot_index}")

    def get_shot_start_time(
        self, path: PureSequencePath, shot_index: int
    ) -> datetime.datetime:
        shot_model = unwrap(self._query_shot_model(path, shot_index))
        return shot_model.start_time.replace(tzinfo=datetime.timezone.utc)

    def get_shot_end_time(
        self, path: PureSequencePath, shot_index: int
    ) -> datetime.datetime:
        shot_model = unwrap(self._query_shot_model(path, shot_index))
        return shot_model.end_time.replace(tzinfo=datetime.timezone.utc)

    def update_start_and_end_time(
        self,
        path: PureSequencePath,
        start_time: Optional[datetime.datetime],
        end_time: Optional[datetime.datetime],
    ) -> None:
        sequence = unwrap(self._query_sequence_model(path))
        sequence.start_time = (
            start_time.astimezone(datetime.timezone.utc).replace(tzinfo=None)
            if start_time
            else None
        )
        sequence.stop_time = (
            end_time.astimezone(datetime.timezone.utc).replace(tzinfo=None)
            if end_time
            else None
        )

    def _query_path_model(
        self, path: PureSequencePath
    ) -> Result[SQLSequencePath, PathNotFoundError]:
        stmt = select(SQLSequencePath).where(SQLSequencePath.path == str(path))
        result = self._get_sql_session().execute(stmt)
        if found := result.scalar():
            return Success(found)
        else:
            return Failure(PathNotFoundError(path))

    def _query_sequence_model(
        self, path: PureSequencePath
    ) -> Result[SQLSequence, PathNotFoundError | PathIsNotSequenceError]:
        path_result = self._query_path_model(path)
        match path_result:
            case Success(path_model):
                stmt = select(SQLSequence).where(SQLSequence.path == path_model)
                result = self._get_sql_session().execute(stmt)
                if found := result.scalar():
                    return Success(found)
                else:
                    return Failure(PathIsNotSequenceError(path))
            case Failure() as failure:
                return failure

    def _query_shot_model(
        self, path: PureSequencePath, shot_index: int
    ) -> Result[
        SQLShot, PathNotFoundError | PathIsNotSequenceError | ShotNotFoundError
    ]:
        sequence_model_result = self._query_sequence_model(path)
        match sequence_model_result:
            case Success(sequence_model):
                stmt = (
                    select(SQLShot)
                    .where(SQLShot.sequence == sequence_model)
                    .where(SQLShot.index == shot_index)
                )
                result = self._get_sql_session().execute(stmt)
                if found := result.scalar():
                    return Success(found)
                else:
                    return Failure(PathIsNotSequenceError(path))
            case Failure() as failure:
                return failure

    def _get_sql_session(self) -> sqlalchemy.orm.Session:
        # noinspection PyProtectedMember
        return self.parent_session._get_sql_session()
