from __future__ import annotations

import datetime
from collections.abc import Mapping, Iterable, Set
from typing import (
    TYPE_CHECKING,
    Optional,
    assert_never,
    assert_type,
)

import attrs
import cattrs
import numpy as np
import sqlalchemy.orm
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from caqtus.types.data import Data
from caqtus.types.data import is_data, DataLabel
from caqtus.types.iteration import (
    IterationConfiguration,
    Unknown,
)
from caqtus.types.parameter import Parameter, ParameterNamespace
from caqtus.types.timelane import TimeLanes
from caqtus.types.units import Quantity
from caqtus.types.variable_name import DottedVariableName
from caqtus.utils import serialization
from caqtus.utils._result import (
    Result,
    Success,
    Failure,
    is_failure_type,
    is_success,
    is_failure,
)
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
from .._data_id import DataId
from .._exception_summary import TracebackSummary
from .._path import PureSequencePath
from .._path_hierarchy import PathNotFoundError, PathHasChildrenError, PathIsRootError
from .._sequence_collection import (
    PathIsSequenceError,
    PathIsNotSequenceError,
    SequenceNotEditableError,
    SequenceStats,
    ShotNotFoundError,
    DataNotFoundError,
    SequenceNotCrashedError,
    InvalidStateTransitionError,
)
from .._sequence_collection import SequenceCollection
from .._shot_id import ShotId
from .._state import State
from ...device import DeviceName, DeviceConfiguration

if TYPE_CHECKING:
    from ._experiment_session import SQLExperimentSession


@attrs.frozen
class SQLSequenceCollection(SequenceCollection):
    parent_session: "SQLExperimentSession"
    serializer: SerializerProtocol

    def is_sequence(self, path: PureSequencePath) -> Result[bool, PathNotFoundError]:
        return _is_sequence(self._get_sql_session(), path)

    def get_contained_sequences(
        self, path: PureSequencePath
    ) -> Result[set[PureSequencePath], PathNotFoundError]:
        path_result = _query_path_model(self._get_sql_session(), path)
        if is_failure_type(path_result, PathNotFoundError):
            return path_result

        result = set()
        if is_failure_type(path_result, PathIsRootError):
            ancestor_id = None
        else:
            ancestor_id = path_result.value.id_

            if path_result.value.sequence is not None:
                result.add(path)

        sequences_query = self.descendant_sequences(ancestor_id)

        query = self._get_sql_session().execute(sequences_query).scalars().all()
        return Success({PureSequencePath(row.path.path) for row in query} | result)

    def descendant_sequences(
        self, ancestor_id: Optional[int]
    ) -> sqlalchemy.sql.Select[tuple[SQLSequence]]:
        """Returns a query for the descendant sequences of the given ancestor.

        The ancestor is not included in the result.
        """

        descendants = self.parent_session.paths.descendants_query(ancestor_id)
        sequences_query = select(SQLSequence).join(
            descendants,
            SQLSequence.path_id == descendants.id_,
        )
        return sequences_query

    def get_contained_running_sequences(
        self, path: PureSequencePath
    ) -> Result[set[PureSequencePath], PathNotFoundError]:
        path_model_result = _query_path_model(self._get_sql_session(), path)

        running_sequences = set()
        if isinstance(path_model_result, Failure):
            if isinstance(path_model_result.error, PathNotFoundError):
                return Failure(path_model_result.error)
            assert_type(path_model_result.error, PathIsRootError)
            parent_id = None
        else:
            path_model = path_model_result.value

            if path_model.sequence is not None:
                if path_model.sequence.state in {State.PREPARING, State.RUNNING}:
                    running_sequences.add(path)
            parent_id = path_model.id_

        sequences_query = self.descendant_sequences(parent_id)
        running_sequences_query = sequences_query.where(
            SQLSequence.state.in_({State.PREPARING, State.RUNNING})
        )

        result = (
            self._get_sql_session().execute(running_sequences_query).scalars().all()
        )
        running_sequences.update(PureSequencePath(row.path.path) for row in result)
        return Success(running_sequences)

    def set_global_parameters(
        self, path: PureSequencePath, parameters: ParameterNamespace
    ) -> None:
        sequence = self._query_sequence_model(path).unwrap()
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
        sequence_model = self._query_sequence_model(sequence).unwrap()
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
    ) -> Success[None] | Failure[PathIsSequenceError] | Failure[PathHasChildrenError]:
        children_result = self.parent_session.paths.get_children(path)
        if is_success(children_result):
            if children_result.value:
                return Failure(PathHasChildrenError(path))
        else:
            if is_failure_type(children_result, PathIsSequenceError):
                return children_result
            elif is_failure_type(children_result, PathNotFoundError):
                creation_result = self.parent_session.paths.create_path(path)
                if is_failure(creation_result):
                    if is_failure_type(creation_result, PathIsSequenceError):
                        return creation_result
                    assert_never(creation_result)
            else:
                assert_never(children_result)

        iteration_content = self.serializer.dump_sequence_iteration(
            iteration_configuration
        )

        new_sequence = SQLSequence(
            path=self._query_path_model(path).unwrap(),
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
        return Success(None)

    def serialize_time_lanes(self, time_lanes: TimeLanes) -> serialization.JSON:
        return self.serializer.unstructure_time_lanes(time_lanes)

    def get_time_lanes(self, sequence_path: PureSequencePath) -> TimeLanes:
        return _get_time_lanes(self._get_sql_session(), sequence_path, self.serializer)

    def set_time_lanes(
        self, sequence_path: PureSequencePath, time_lanes: TimeLanes
    ) -> None:
        sequence_model = self._query_sequence_model(sequence_path).unwrap()
        if not sequence_model.state.is_editable():
            raise SequenceNotEditableError(sequence_path)
        sequence_model.time_lanes.content = self.serialize_time_lanes(time_lanes)

    def get_state(
        self, path: PureSequencePath
    ) -> Success[State] | Failure[PathNotFoundError] | Failure[PathIsNotSequenceError]:
        result = self._query_sequence_model(path)
        return result.map(lambda sequence: sequence.state)

    def get_exception(
        self, path: PureSequencePath
    ) -> (
        Success[Optional[TracebackSummary]]
        | Failure[PathNotFoundError]
        | Failure[PathIsNotSequenceError]
        | Failure[SequenceNotCrashedError]
    ):
        return _get_exceptions(self._get_sql_session(), path)

    def set_exception(
        self, path: PureSequencePath, exception: TracebackSummary
    ) -> (
        Success[None]
        | Failure[PathNotFoundError]
        | Failure[PathIsNotSequenceError]
        | Failure[SequenceNotCrashedError]
    ):
        return _set_exception(self._get_sql_session(), path, exception)

    def set_state(
        self, path: PureSequencePath, state: State
    ) -> Success[None] | Failure[PathNotFoundError] | Failure[PathIsNotSequenceError]:
        return _set_state(self._get_sql_session(), path, state)

    def set_device_configurations(
        self,
        path: PureSequencePath,
        device_configurations: Mapping[DeviceName, DeviceConfiguration],
    ) -> None:
        sequence = self._query_sequence_model(path).unwrap()
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
        sequence = self._query_sequence_model(path).unwrap()
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
    ) -> (
        Success[SequenceStats]
        | Failure[PathNotFoundError]
        | Failure[PathIsNotSequenceError]
    ):
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
        sequence = self._query_sequence_model(path).unwrap()
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
    ) -> Result[list[ShotId], PathNotFoundError | PathIsNotSequenceError]:
        return _get_shots(self._get_sql_session(), path)

    def get_shot_parameters(
        self, path: PureSequencePath, shot_index: int
    ) -> Mapping[DottedVariableName, Parameter]:
        return _get_shot_parameters(self._get_sql_session(), path, shot_index)

    def get_all_shot_data(
        self, path: PureSequencePath, shot_index: int
    ) -> dict[DataLabel, Data]:
        return _get_all_shot_data(self._get_sql_session(), path, shot_index)

    def get_shot_data_by_label(self, data: DataId) -> Data:
        return _get_shot_data_by_label(self._get_sql_session(), data)

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
        sequence = self._query_sequence_model(path).unwrap()
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
    ) -> Result[SQLSequencePath, PathNotFoundError | PathIsRootError]:
        return _query_path_model(self._get_sql_session(), path)

    def _query_sequence_model(
        self, path: PureSequencePath
    ) -> (
        Success[SQLSequence]
        | Failure[PathNotFoundError]
        | Failure[PathIsNotSequenceError]
    ):
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
    path_model_result = _query_path_model(session, path)
    if isinstance(path_model_result, Failure):
        if isinstance(path_model_result.error, PathNotFoundError):
            return Failure(path_model_result.error)
        else:
            assert_type(path_model_result.error, PathIsRootError)
            return Success(False)
    else:
        path_model = path_model_result.value
        return Success(bool(path_model.sequence))


def _get_exceptions(
    session: Session, path: PureSequencePath
) -> (
    Success[Optional[TracebackSummary]]
    | Failure[PathNotFoundError]
    | Failure[PathIsNotSequenceError]
    | Failure[SequenceNotCrashedError]
):
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
) -> (
    Success[None]
    | Failure[PathNotFoundError]
    | Failure[PathIsNotSequenceError]
    | Failure[SequenceNotCrashedError]
):
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
) -> (
    Success[SequenceStats]
    | Failure[PathNotFoundError]
    | Failure[PathIsNotSequenceError]
):
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


def _set_state(
    session: Session, path: PureSequencePath, state: State
) -> Success[None] | Failure[PathNotFoundError] | Failure[PathIsNotSequenceError]:
    sequence_result = _query_sequence_model(session, path)
    if is_failure(sequence_result):
        return sequence_result
    sequence = sequence_result.value
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
            session.delete(sequence.exception_traceback)
        delete_device_configurations = sqlalchemy.delete(SQLDeviceConfiguration).where(
            SQLDeviceConfiguration.sequence == sequence
        )
        session.execute(delete_device_configurations)

        delete_shots = sqlalchemy.delete(SQLShot).where(SQLShot.sequence == sequence)
        session.execute(delete_shots)
    elif state == State.RUNNING:
        sequence.start_time = datetime.datetime.now(tz=datetime.timezone.utc).replace(
            tzinfo=None
        )
    elif state in (State.INTERRUPTED, State.CRASHED, State.FINISHED):
        sequence.stop_time = datetime.datetime.now(tz=datetime.timezone.utc).replace(
            tzinfo=None
        )

    assert sequence.state == state
    return Success(None)


def _get_sequence_global_parameters(
    session: Session, path: PureSequencePath
) -> ParameterNamespace:
    sequence = _query_sequence_model(session, path).unwrap()

    if sequence.state == State.DRAFT:
        raise RuntimeError("Sequence has not been prepared yet")

    parameters_content = sequence.parameters.content

    return serialization.converters["json"].structure(
        parameters_content, ParameterNamespace
    )


def _get_iteration_configuration(
    session: Session, sequence: PureSequencePath, serializer: SerializerProtocol
) -> IterationConfiguration:
    sequence_model = _query_sequence_model(session, sequence).unwrap()
    return serializer.construct_sequence_iteration(
        sequence_model.iteration.content,
    )


def _get_time_lanes(
    session: Session, sequence_path: PureSequencePath, serializer: SerializerProtocol
) -> TimeLanes:
    sequence_model = _query_sequence_model(session, sequence_path).unwrap()
    return serializer.structure_time_lanes(sequence_model.time_lanes.content)


def _get_shots(
    session: Session, path: PureSequencePath
) -> Result[list[ShotId], PathNotFoundError | PathIsNotSequenceError]:
    sql_sequence = _query_sequence_model(session, path)

    def extract_shots(sql_sequence: SQLSequence) -> list[ShotId]:
        return [ShotId(path, shot.index) for shot in sql_sequence.shots]

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
    _query_shot_model(session, path, shot_index).unwrap()
    raise AssertionError("Unreachable code")


def _get_all_shot_data(
    session: Session, path: PureSequencePath, shot_index: int
) -> dict[DataLabel, Data]:
    shot_model = _query_shot_model(session, path, shot_index).unwrap()
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
    data: DataId,
) -> Data:
    return _get_shot_data_by_labels(
        session, data.shot_id.sequence_path, data.shot_id.index, {data.data_label}
    )[data.data_label]


def _get_shot_data_by_labels(
    session: Session,
    path: PureSequencePath,
    shot_index: int,
    data_labels: Set[DataLabel],
) -> dict[DataLabel, Data]:
    content = _query_data_model(session, path, shot_index, data_labels).unwrap()

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
    shot_model = _query_shot_model(session, path, shot_index).unwrap()
    return shot_model.start_time.replace(tzinfo=datetime.timezone.utc)


def _get_shot_end_time(
    session: Session, path: PureSequencePath, shot_index: int
) -> datetime.datetime:
    shot_model = _query_shot_model(session, path, shot_index).unwrap()
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
) -> (
    Success[SQLSequence] | Failure[PathNotFoundError] | Failure[PathIsNotSequenceError]
):
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
        if isinstance(path_result, Success):
            return Failure(PathIsNotSequenceError(path))
        else:
            if isinstance(path_result.error, PathNotFoundError):
                return Failure(path_result.error)
            else:
                assert_type(path_result.error, PathIsRootError)
                return Failure(PathIsNotSequenceError(path))


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
            case _:
                assert_never(sequence_model_result)
