import datetime
import functools
import uuid
from collections.abc import Callable, Set, Mapping
from typing import TYPE_CHECKING

import attrs
import sqlalchemy.orm
from returns.result import Result
from returns.result import Success, Failure
from sqlalchemy import select

from core.types.expression import Expression
from core.types.parameter import Parameter
from core.types.variable_name import DottedVariableName
from util import serialization
from ._path_table import SQLSequencePath
from ._sequence_table import (
    SQLSequence,
    SQLIterationConfiguration,
    SQLSequenceDeviceUUID,
    SQLSequenceConstantTableUUID,
    SQLTimelanes,
)
from ._shot_tables import SQLShot, SQLShotParameter
from .._return_or_raise import unwrap
from ..path import PureSequencePath, BoundSequencePath
from ..path_hierarchy import PathNotFoundError, PathHasChildrenError
from ..sequence import Sequence, Shot
from ..sequence.iteration_configuration import (
    IterationConfiguration,
    StepsConfiguration,
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
from ..shot import TimeLane, DigitalTimeLane, TimeLanes
from ...types.units import Quantity

if TYPE_CHECKING:
    from ._experiment_session import SQLExperimentSession


@attrs.define
class SequenceSerializer:
    iteration_serializer: Callable[[IterationConfiguration], serialization.JSON]
    iteration_constructor: Callable[[serialization.JSON], IterationConfiguration]
    time_lane_serializer: Callable[[TimeLane], serialization.JSON]
    time_lane_constructor: Callable[[serialization.JSON], TimeLane]


@functools.singledispatch
def default_iteration_configuration_serializer(
    iteration_configuration: IterationConfiguration,
) -> serialization.JSON:
    raise TypeError(
        f"Cannot serialize iteration configuration of type "
        f"{type(iteration_configuration)}"
    )


@default_iteration_configuration_serializer.register
def _(
    iteration_configuration: StepsConfiguration,
):
    content = serialization.converters["json"].unstructure(iteration_configuration)
    content["type"] = "steps"
    return content


def default_iteration_configuration_constructor(
    iteration_content: serialization.JSON,
) -> IterationConfiguration:
    iteration_type = iteration_content.pop("type")
    if iteration_type == "steps":
        return serialization.converters["json"].structure(
            iteration_content, StepsConfiguration
        )
    else:
        raise ValueError(f"Unknown iteration type {iteration_type}")


@functools.singledispatch
def default_time_lane_serializer(time_lane: TimeLane) -> serialization.JSON:
    raise TypeError(f"Cannot serialize time lane of type {type(time_lane)}")


@default_time_lane_serializer.register
def _(time_lane: DigitalTimeLane):
    content = serialization.converters["json"].unstructure(time_lane, DigitalTimeLane)
    content["type"] = "digital"
    return content


def default_time_lane_constructor(
    time_lane_content: serialization.JSON,
) -> TimeLane:
    time_lane_type = time_lane_content.pop("type")
    if time_lane_type == "digital":
        return serialization.converters["json"].structure(
            time_lane_content, DigitalTimeLane
        )
    else:
        raise ValueError(f"Unknown time lane type {time_lane_type}")


default_sequence_serializer = SequenceSerializer(
    iteration_serializer=default_iteration_configuration_serializer,
    iteration_constructor=default_iteration_configuration_constructor,
    time_lane_serializer=default_time_lane_serializer,
    time_lane_constructor=default_time_lane_constructor,
)


@attrs.frozen
class SQLSequenceCollection(SequenceCollection):
    parent_session: "SQLExperimentSession"
    serializer: SequenceSerializer

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

    def get_iteration_configuration(
        self, sequence: PureSequencePath
    ) -> IterationConfiguration:
        sequence_model = unwrap(self._query_sequence_model(sequence))
        return self.serializer.iteration_constructor(
            sequence_model.iteration_config.content,
        )

    def set_iteration_configuration(
        self, sequence: Sequence, iteration_configuration: IterationConfiguration
    ) -> None:
        sequence_model = unwrap(self._query_sequence_model(sequence.path))
        if not sequence_model.state.is_editable():
            raise SequenceNotEditableError(sequence.path)
        iteration_content = self.serializer.iteration_serializer(
            iteration_configuration
        )
        sequence_model.iteration_config.content = iteration_content

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
        iteration_content = self.serializer.iteration_serializer(
            iteration_configuration
        )
        new_sequence = SQLSequence(
            path=unwrap(self._query_path_model(path)),
            iteration_config=SQLIterationConfiguration(content=iteration_content),
            time_lanes_config=SQLTimelanes(
                content=self.serialize_time_lanes(time_lanes)
            ),
            state=State.DRAFT,
            device_uuids=set(),
            constant_table_uuids=set(),
            start_time=None,
            stop_time=None,
        )
        self._get_sql_session().add(new_sequence)
        return Sequence(BoundSequencePath(path, self.parent_session))

    def serialize_time_lanes(self, time_lanes: TimeLanes) -> serialization.JSON:
        return dict(
            step_names=serialization.converters["json"].unstructure(
                time_lanes.step_names, list[str]
            ),
            step_durations=serialization.converters["json"].unstructure(
                time_lanes.step_durations, list[Expression]
            ),
            lanes={
                lane: self.serializer.time_lane_serializer(time_lane)
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
                lane: self.serializer.time_lane_constructor(time_lane_content)
                for lane, time_lane_content in time_lanes_content["lanes"].items()
            },
        )

    def get_time_lanes(self, sequence_path: PureSequencePath) -> TimeLanes:
        sequence_model = unwrap(self._query_sequence_model(sequence_path))
        return self.construct_time_lanes(sequence_model.time_lanes_config.content)

    def set_time_lanes(
        self, sequence_path: PureSequencePath, time_lanes: TimeLanes
    ) -> None:
        sequence_model = unwrap(self._query_sequence_model(sequence_path))
        if not sequence_model.state.is_editable():
            raise SequenceNotEditableError(sequence_path)
        sequence_model.time_lanes_config.content = self.serialize_time_lanes(time_lanes)

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
            sequence.device_uuids = set()
            sequence.constant_table_uuids = set()
            sequence.start_time = None
            sequence.stop_time = None
        elif state == State.RUNNING:
            sequence.start_date = datetime.datetime.now(tz=datetime.timezone.utc)
        elif state in (State.INTERRUPTED, State.CRASHED, State.FINISHED):
            sequence.stop_date = datetime.datetime.now(tz=datetime.timezone.utc)

    def set_device_configuration_uuids(
        self, path: PureSequencePath, device_configuration_uuids: Set[uuid.UUID]
    ) -> None:
        sequence = unwrap(self._query_sequence_model(path))
        if sequence.state != State.PREPARING:
            raise SequenceNotEditableError(path)
        sql_device_uuids = {
            SQLSequenceDeviceUUID(device_configuration_uuid=uuid_)
            for uuid_ in device_configuration_uuids
        }
        sequence.device_configuration_uuids = sql_device_uuids

    def set_constant_table_uuids(
        self, path: PureSequencePath, constant_table_uuids: Set[uuid.UUID]
    ) -> None:
        sequence = unwrap(self._query_sequence_model(path))
        if sequence.state != State.PREPARING:
            raise SequenceNotEditableError(path)
        sql_constant_table_uuids = {
            SQLSequenceConstantTableUUID(constant_table_uuid=uuid_)
            for uuid_ in constant_table_uuids
        }
        sequence.constant_table_uuids = sql_constant_table_uuids

    def get_stats(
        self, path: PureSequencePath
    ) -> Result[SequenceStats, PathNotFoundError | PathIsNotSequenceError]:
        result = self._query_sequence_model(path)

        def extract_stats(sequence: SQLSequence) -> SequenceStats:
            return SequenceStats(
                state=sequence.state,
                start_time=sequence.start_time,
                stop_time=sequence.stop_time,
            )

        return result.map(extract_stats)

    def create_shot(
        self,
        path: PureSequencePath,
        shot_index: int,
        shot_parameters: Mapping[DottedVariableName, Parameter],
        shot_start_time: datetime.datetime,
        shot_end_time: datetime.datetime,
    ) -> None:
        sequence = unwrap(self._query_sequence_model(path))
        if sequence.state != State.RUNNING:
            raise RuntimeError("Can't create shot in sequence that is not running")

        parameters = [
            SQLShotParameter(name=variable_name, value=parameter)
            for variable_name, parameter in self.serialize_shot_parameters(
                shot_parameters
            ).items()
        ]
        shot = SQLShot(
            sequence=sequence,
            index=shot_index,
            parameters=parameters,
            start_time=shot_start_time,
            end_time=shot_end_time,
        )
        self._get_sql_session().add(shot)

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

    def get_shots(self, path: PureSequencePath) -> list[Shot]:
        sql_sequence = unwrap(self._query_sequence_model(path))
        sequence = Sequence(BoundSequencePath(path, self.parent_session))

        return [Shot(sequence, shot.index) for shot in sql_sequence.shots]

    def get_shot_parameters(
        self, path: PureSequencePath, shot_index: int
    ) -> Mapping[DottedVariableName, Parameter]:
        shot_model = unwrap(self._query_shot_model(path, shot_index))
        parameters = {
            DottedVariableName(parameter.name): serialization.converters[
                "json"
            ].structure(parameter.value, bool | int | float | Quantity)
            for parameter in shot_model.parameters
        }
        return parameters

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
