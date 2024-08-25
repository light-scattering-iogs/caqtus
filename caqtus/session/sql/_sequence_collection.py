from __future__ import annotations

import datetime
from collections.abc import Mapping, Set
from typing import TYPE_CHECKING, Optional, assert_never, Iterable

import attrs
import cattrs
import numpy as np
import sqlalchemy.orm
from returns.result import Result
from returns.result import Success, Failure
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from caqtus.device import DeviceConfiguration, DeviceName
from caqtus.types.data import DataLabel, Data, is_data
from caqtus.types.iteration import (
    IterationConfiguration,
    Unknown,
)
from caqtus.types.parameter import Parameter, ParameterNamespace
from caqtus.types.timelane import TimeLanes
from caqtus.types.units import Quantity
from caqtus.types.variable_name import DottedVariableName
from caqtus.utils import serialization
from ._path_hierarchy import _query_path_model
from ._path_table import SQLSequencePath
from ._sequence_table import (
    SQLSequence,
    SQLIterationConfiguration,
    SQLTimelanes,
    SQLDeviceConfiguration,
    SQLSequenceParameters,
    SQLExceptionTraceback,
)
from ._serializer import SerializerProtocol
from ._shot_tables import SQLShot, SQLShotParameter, SQLShotArray, SQLStructuredShotData
from .._exception_summary import TracebackSummary
from .._path import PureSequencePath
from .._path_hierarchy import PathNotFoundError, PathHasChildrenError
from .._return_or_raise import unwrap
from .._sequence_collection import (
    PathIsSequenceError,
    PathIsNotSequenceError,
    InvalidStateTransitionError,
    SequenceNotEditableError,
    SequenceStats,
    ShotNotFoundError,
    PureShot,
    DataNotFoundError,
    SequenceNotCrashedError,
)
from .._sequence_collection import SequenceCollection
from .._state import State

if TYPE_CHECKING:
    from ._experiment_session import SQLExperimentSession


@attrs.frozen
class SQLSequenceCollection(SequenceCollection):
    parent_session: "SQLExperimentSession"
    serializer: SerializerProtocol

    def is_sequence(self, path: PureSequencePath) -> Result[bool, PathNotFoundError]:
        return _is_sequence(self._get_sql_session(), path)

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
        return _get_sequence_global_parameters(self._get_sql_session(), path)

    def get_iteration_configuration(
        self, sequence: PureSequencePath
    ) -> IterationConfiguration:
        return _get_iteration_configuration(
            self._get_sql_session(), sequence, self.serializer
        )

    def set_iteration_configuration(
        self,
        sequence: PureSequencePath,
        iteration_configuration: IterationConfiguration,
    ) -> None:
        sequence_model = unwrap(self._query_sequence_model(sequence))
        if not sequence_model.state.is_editable():
            raise SequenceNotEditableError(sequence)
        iteration_content = self.serializer.dump_sequence_iteration(
            iteration_configuration
        )
        sequence_model.iteration.content = iteration_content
        expected_number_shots = iteration_configuration.expected_number_shots()
        sequence_model.expected_number_of_shots = _convert_from_unknown(
            expected_number_shots
        )

    def create(
        self,
        path: PureSequencePath,
        iteration_configuration: IterationConfiguration,
        time_lanes: TimeLanes,
    ) -> None:
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
            expected_number_of_shots=_convert_from_unknown(
                iteration_configuration.expected_number_shots()
            ),
        )
        self._get_sql_session().add(new_sequence)

    def serialize_time_lanes(self, time_lanes: TimeLanes) -> serialization.JSON:
        return self.serializer.unstructure_time_lanes(time_lanes)

    def get_time_lanes(self, sequence_path: PureSequencePath) -> TimeLanes:
        return _get_time_lanes(self._get_sql_session(), sequence_path, self.serializer)

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

    def get_exception(self, path: PureSequencePath) -> Result[
        Optional[TracebackSummary],
        PathNotFoundError | PathIsNotSequenceError | SequenceNotCrashedError,
    ]:
        return _get_exceptions(self._get_sql_session(), path)

    def set_exception(
        self, path: PureSequencePath, exception: TracebackSummary
    ) -> Result[
        None, PathNotFoundError | PathIsNotSequenceError | SequenceNotCrashedError
    ]:
        return _set_exception(self._get_sql_session(), path, exception)

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
            if sequence.exception_traceback:
                self._get_sql_session().delete(sequence.exception_traceback)
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

        assert sequence.state == state

    def set_device_configurations(
        self,
        path: PureSequencePath,
        device_configurations: Mapping[DeviceName, DeviceConfiguration],
    ) -> None:
        sequence = unwrap(self._query_sequence_model(path))
        if sequence.state != State.PREPARING:
            raise SequenceNotEditableError(path)
        sql_device_configs = []
        for name, device_configuration in device_configurations.items():
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
        return _get_stats(self._get_sql_session(), path)

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
    ) -> Result[list[PureShot], PathNotFoundError | PathIsNotSequenceError]:
        return _get_shots(self._get_sql_session(), path)

    def get_shot_parameters(
        self, path: PureSequencePath, shot_index: int
    ) -> Mapping[DottedVariableName, Parameter]:
        return _get_shot_parameters(self._get_sql_session(), path, shot_index)

    def get_all_shot_data(
        self, path: PureSequencePath, shot_index: int
    ) -> dict[DataLabel, Data]:
        return _get_all_shot_data(self._get_sql_session(), path, shot_index)

    def get_shot_data_by_label(
        self, path: PureSequencePath, shot_index: int, data_label: DataLabel
    ) -> Data:
        return _get_shot_data_by_label(
            self._get_sql_session(), path, shot_index, data_label
        )

    def get_shot_data_by_labels(
        self, path: PureSequencePath, shot_index: int, data_labels: Set[DataLabel]
    ) -> Mapping[DataLabel, Data]:
        return _get_shot_data_by_labels(
            self._get_sql_session(), path, shot_index, data_labels
        )

    def get_shot_start_time(
        self, path: PureSequencePath, shot_index: int
    ) -> datetime.datetime:
        return _get_shot_start_time(self._get_sql_session(), path, shot_index)

    def get_shot_end_time(
        self, path: PureSequencePath, shot_index: int
    ) -> datetime.datetime:
        return _get_shot_end_time(self._get_sql_session(), path, shot_index)

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

    def get_sequences_in_state(self, state: State) -> Iterable[PureSequencePath]:
        stmt = (
            select(SQLSequencePath).join(SQLSequence).where(SQLSequence.state == state)
        )
        result = self._get_sql_session().execute(stmt).scalars().all()
        return (PureSequencePath(row.path) for row in result)

    def _query_path_model(
        self, path: PureSequencePath
    ) -> Result[SQLSequencePath, PathNotFoundError]:
        return _query_path_model(self._get_sql_session(), path)

    def _query_sequence_model(
        self, path: PureSequencePath
    ) -> Result[SQLSequence, PathNotFoundError | PathIsNotSequenceError]:
        return _query_sequence_model(self._get_sql_session(), path)

    def _query_shot_model(
        self, path: PureSequencePath, shot_index: int
    ) -> Result[
        SQLShot, PathNotFoundError | PathIsNotSequenceError | ShotNotFoundError
    ]:
        return _query_shot_model(self._get_sql_session(), path, shot_index)

    def _get_sql_session(self) -> sqlalchemy.orm.Session:
        # noinspection PyProtectedMember
        return self.parent_session._get_sql_session()


def _convert_from_unknown(value: int | Unknown) -> Optional[int]:
    if isinstance(value, Unknown):
        return None
    elif isinstance(value, int):
        return value
    else:
        assert_never(value)


def _convert_to_unknown(value: Optional[int]) -> int | Unknown:
    if value is None:
        return Unknown()
    elif isinstance(value, int):
        return value
    else:
        assert_never(value)


def _is_sequence(
    session: Session, path: PureSequencePath
) -> Result[bool, PathNotFoundError]:
    if path.is_root():
        return Success(False)
    return _query_path_model(session, path).map(
        lambda path_model: bool(path_model.sequence)
    )


def _get_exceptions(session: Session, path: PureSequencePath) -> Result[
    Optional[TracebackSummary],
    PathNotFoundError | PathIsNotSequenceError | SequenceNotCrashedError,
]:
    sequence_model_query = _query_sequence_model(session, path)
    match sequence_model_query:
        case Success(sequence_model):
            assert isinstance(sequence_model, SQLSequence)
            if sequence_model.state != State.CRASHED:
                return Failure(SequenceNotCrashedError(path))
            exception_model = sequence_model.exception_traceback
            if exception_model is None:
                return Success(None)
            else:
                traceback_summary = cattrs.structure(
                    exception_model.content, TracebackSummary
                )
                return Success(traceback_summary)
        case Failure() as failure:
            return failure


def _set_exception(
    session: Session, path: PureSequencePath, exception: TracebackSummary
) -> Result[None, PathNotFoundError | PathIsNotSequenceError | SequenceNotCrashedError]:
    sequence_model_query = _query_sequence_model(session, path)
    match sequence_model_query:
        case Success(sequence_model):
            assert isinstance(sequence_model, SQLSequence)
            if sequence_model.state != State.CRASHED:
                return Failure(SequenceNotCrashedError(path))
            if sequence_model.exception_traceback is not None:
                raise RuntimeError("Exception already set")
            content = cattrs.unstructure(exception, TracebackSummary)
            sequence_model.exception_traceback = SQLExceptionTraceback(content=content)
            return Success(None)
        case Failure() as failure:
            return failure


def _get_stats(
    session: Session, path: PureSequencePath
) -> Result[SequenceStats, PathNotFoundError | PathIsNotSequenceError]:
    result = _query_sequence_model(session, path)

    def extract_stats(sequence: SQLSequence) -> SequenceStats:
        number_shot_query = select(func.count()).select_from(
            select(SQLShot).where(SQLShot.sequence == sequence).subquery()
        )
        number_shot_run = session.execute(number_shot_query).scalar_one()
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
            expected_number_shots=_convert_to_unknown(
                sequence.expected_number_of_shots
            ),
        )

    return result.map(extract_stats)


def _get_sequence_global_parameters(
    session: Session, path: PureSequencePath
) -> ParameterNamespace:
    sequence = unwrap(_query_sequence_model(session, path))

    if sequence.state == State.DRAFT:
        raise RuntimeError("Sequence has not been prepared yet")

    parameters_content = sequence.parameters.content

    return serialization.converters["json"].structure(
        parameters_content, ParameterNamespace
    )


def _get_iteration_configuration(
    session: Session, sequence: PureSequencePath, serializer: SerializerProtocol
) -> IterationConfiguration:
    sequence_model = unwrap(_query_sequence_model(session, sequence))
    return serializer.construct_sequence_iteration(
        sequence_model.iteration.content,
    )


def _get_time_lanes(
    session: Session, sequence_path: PureSequencePath, serializer: SerializerProtocol
) -> TimeLanes:
    sequence_model = unwrap(_query_sequence_model(session, sequence_path))
    return serializer.structure_time_lanes(sequence_model.time_lanes.content)


def _get_shots(
    session: Session, path: PureSequencePath
) -> Result[list[PureShot], PathNotFoundError | PathIsNotSequenceError]:
    sql_sequence = _query_sequence_model(session, path)

    def extract_shots(sql_sequence: SQLSequence) -> list[PureShot]:
        return [PureShot(path, shot.index) for shot in sql_sequence.shots]

    return sql_sequence.map(extract_shots)


def _get_shot_parameters(
    session: Session, path: PureSequencePath, shot_index: int
) -> Mapping[DottedVariableName, Parameter]:
    stmt = (
        select(SQLShotParameter.content)
        .join(SQLShot)
        .where(SQLShot.index == shot_index)
        .join(SQLSequence)
        .join(SQLSequencePath)
        .where(SQLSequencePath.path == str(path))
    )

    result = session.execute(stmt).scalar_one_or_none()
    if result is not None:
        return serialization.converters["json"].structure(
            result, dict[DottedVariableName, bool | int | float | Quantity]
        )
    # This will raise the proper error if the shot was not found.
    unwrap(_query_shot_model(session, path, shot_index))
    assert False, "Unreachable"


def _get_all_shot_data(
    session: Session, path: PureSequencePath, shot_index: int
) -> dict[DataLabel, Data]:
    shot_model = unwrap(_query_shot_model(session, path, shot_index))
    arrays = shot_model.array_data
    structured_data = shot_model.structured_data
    result = {}
    for array in arrays:
        result[array.label] = np.frombuffer(array.bytes_, dtype=array.dtype).reshape(
            array.shape
        )
    for data in structured_data:
        result[data.label] = data.content
    return result


def _get_shot_data_by_label(
    session: Session,
    path: PureSequencePath,
    shot_index: int,
    data_label: DataLabel,
) -> Data:
    return _get_shot_data_by_labels(session, path, shot_index, {data_label})[data_label]


def _get_shot_data_by_labels(
    session: Session,
    path: PureSequencePath,
    shot_index: int,
    data_labels: Set[DataLabel],
) -> dict[DataLabel, Data]:
    content = unwrap(_query_data_model(session, path, shot_index, data_labels))

    data = {}

    for label, value in content.items():
        if isinstance(value, SQLStructuredShotData):
            data[label] = value.content
        elif isinstance(value, SQLShotArray):
            data[label] = np.frombuffer(value.bytes_, dtype=value.dtype).reshape(
                value.shape
            )
        else:
            assert_never(value)
    return data


def _get_shot_start_time(
    session: Session, path: PureSequencePath, shot_index: int
) -> datetime.datetime:
    shot_model = unwrap(_query_shot_model(session, path, shot_index))
    return shot_model.start_time.replace(tzinfo=datetime.timezone.utc)


def _get_shot_end_time(
    session: Session, path: PureSequencePath, shot_index: int
) -> datetime.datetime:
    shot_model = unwrap(_query_shot_model(session, path, shot_index))
    return shot_model.end_time.replace(tzinfo=datetime.timezone.utc)


def _query_data_model(
    session: Session,
    path: PureSequencePath,
    shot_index: int,
    data_labels: Set[DataLabel],
) -> Result[
    dict[DataLabel, SQLShotArray | SQLStructuredShotData],
    PathNotFoundError | PathIsNotSequenceError | ShotNotFoundError | DataNotFoundError,
]:
    data = {}
    data_labels = set(data_labels)
    stmt = (
        select(SQLStructuredShotData)
        .where(SQLStructuredShotData.label.in_(data_labels))
        .join(SQLShot)
        .where(SQLShot.index == shot_index)
        .join(SQLSequence)
        .join(SQLSequencePath)
        .where(SQLSequencePath.path == str(path))
    )
    results = session.execute(stmt).all()
    for (result,) in results:
        data[result.label] = result
        data_labels.remove(result.label)
    if not data_labels:
        return Success(data)
    stmt = (
        select(SQLShotArray)
        .where(SQLShotArray.label.in_(data_labels))
        .join(SQLShot)
        .where(SQLShot.index == shot_index)
        .join(SQLSequence)
        .join(SQLSequencePath)
        .where(SQLSequencePath.path == str(path))
    )
    results = session.execute(stmt).all()
    for (result,) in results:
        data[result.label] = result
        data_labels.remove(result.label)
    if not data_labels:
        return Success(data)
    shot_result = _query_shot_model(session, path, shot_index)
    match shot_result:
        case Success():
            return Failure(DataNotFoundError(data_labels))
        case Failure() as failure:
            return failure


def _query_sequence_model(
    session: Session, path: PureSequencePath
) -> Result[SQLSequence, PathNotFoundError | PathIsNotSequenceError]:
    stmt = (
        select(SQLSequence)
        .join(SQLSequencePath)
        .where(SQLSequencePath.path == str(path))
    )
    result = session.execute(stmt).scalar_one_or_none()
    if result is not None:
        return Success(result)
    else:
        # If we are not is the happy path, we need to check the reason why to be able to
        # return the correct error.
        path_result = _query_path_model(session, path)
        match path_result:
            case Success():
                return Failure(PathIsNotSequenceError(path))
            case Failure() as failure:
                return failure


def _query_shot_model(
    session: Session, path: PureSequencePath, shot_index: int
) -> Result[SQLShot, PathNotFoundError | PathIsNotSequenceError | ShotNotFoundError]:
    stmt = (
        select(SQLShot)
        .where(SQLShot.index == shot_index)
        .join(SQLSequence)
        .join(SQLSequencePath)
        .where(SQLSequencePath.path == str(path))
    )

    result = session.execute(stmt).scalar_one_or_none()
    if result is not None:
        return Success(result)
    else:
        # This function is fast for the happy path were the shot exists, but if it was
        # not found, we need to check the reason why to be able to return the correct
        # error.
        sequence_model_result = _query_sequence_model(session, path)
        match sequence_model_result:
            case Success():
                return Failure(
                    ShotNotFoundError(
                        f"Shot {shot_index} not found for sequence {path}"
                    )
                )
            case Failure() as failure:
                return failure
