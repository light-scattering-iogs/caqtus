import asyncio
import contextlib
from datetime import datetime
from typing import Callable, Concatenate, TypeVar, ParamSpec, Mapping, Optional, Self

import attrs
from returns.result import Result
from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction
from sqlalchemy.orm import Session

from caqtus.types.parameter import Parameter
from caqtus.types.variable_name import DottedVariableName
from ._experiment_session import _get_global_parameters, _set_global_parameters
from ._path_hierarchy import _does_path_exists, _get_children, _get_path_creation_date
from ._sequence_collection import (
    _get_stats,
    _is_sequence,
    _get_sequence_global_parameters,
    _get_time_lanes,
    _get_iteration_configuration,
    _get_shots,
    _get_shot_parameters,
    _get_shot_end_time,
    _get_shot_start_time,
    _get_shot_data_by_label,
    _get_all_shot_data,
)
from ._serializer import Serializer
from .. import ParameterNamespace, PureSequencePath
from ..async_session import (
    AsyncExperimentSession,
    AsyncPathHierarchy,
    AsyncSequenceCollection,
)
from ..experiment_session import ExperimentSessionNotActiveError
from ..path_hierarchy import PathNotFoundError, PathIsRootError
from ..sequence.iteration_configuration import IterationConfiguration
from ..sequence_collection import (
    PathIsSequenceError,
    SequenceStats,
    PathIsNotSequenceError,
    PureShot,
)
from ..shot import TimeLanes
from ...types.data import DataLabel, Data

_T = TypeVar("_T")
_P = ParamSpec("_P")


class AsyncSQLExperimentSession(AsyncExperimentSession):
    def __init__(self, async_session: AsyncSession, serializer: Serializer):
        self._async_session = async_session
        self._transaction: Optional[AsyncSessionTransaction] = None

        self.paths = AsyncSQLPathHierarchy(parent_session=self)
        self.sequences = AsyncSQLSequenceCollection(
            parent_session=self, serializer=serializer
        )
        self._exit_stack = contextlib.AsyncExitStack()

    async def __aenter__(self) -> Self:
        if self._transaction is not None:
            error = RuntimeError("Session has already been activated")
            error.add_note(
                "You cannot reactivate a session, you must create a new one."
            )
        await self._exit_stack.__aenter__()
        await self._exit_stack.enter_async_context(self._async_session)
        try:
            self._transaction = await self._exit_stack.enter_async_context(
                self._async_session.begin()
            )
        except Exception:
            await self._exit_stack.aclose()
            raise
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)

    async def get_global_parameters(self) -> ParameterNamespace:
        return await self._run_sync(_get_global_parameters)

    async def set_global_parameters(self, parameters: ParameterNamespace) -> None:
        return await self._run_sync(_set_global_parameters, parameters)

    async def _run_sync(
        self,
        fun: Callable[Concatenate[Session, _P], _T],
        *args: _P.args,
        **kwargs: _P.kwargs
    ) -> _T:
        return await self._session().run_sync(fun, *args, **kwargs)

    def _session(self) -> AsyncSession:
        if self._transaction is None:
            raise ExperimentSessionNotActiveError(
                "Experiment session was not activated"
            )
        return self._async_session


class ThreadedAsyncSQLExperimentSession(AsyncSQLExperimentSession):
    def __init__(self, session: Session, serializer: Serializer):
        self._session = session
        self._is_active = False

        self.paths = AsyncSQLPathHierarchy(parent_session=self)
        self.sequences = AsyncSQLSequenceCollection(
            parent_session=self, serializer=serializer
        )

    async def __aenter__(self):
        if self._is_active:
            raise RuntimeError("Session is already active")
        self._transaction = await asyncio.to_thread(self._session.begin().__enter__)
        self._is_active = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await asyncio.to_thread(self._transaction.__exit__, exc_type, exc_val, exc_tb)
        self._transaction = None
        self._is_active = False

    async def _run_sync(
        self,
        fun: Callable[Concatenate[Session, _P], _T],
        *args: _P.args,
        **kwargs: _P.kwargs
    ) -> _T:
        return await asyncio.to_thread(fun, self._session, *args, **kwargs)


@attrs.frozen
class AsyncSQLPathHierarchy(AsyncPathHierarchy):
    parent_session: AsyncSQLExperimentSession

    async def does_path_exists(self, path: PureSequencePath) -> bool:
        return await self._run_sync(_does_path_exists, path)

    async def get_children(
        self, path: PureSequencePath
    ) -> Result[set[PureSequencePath], PathNotFoundError | PathIsSequenceError]:
        return await self._run_sync(_get_children, path)

    async def get_path_creation_date(
        self, path: PureSequencePath
    ) -> Result[datetime, PathNotFoundError | PathIsRootError]:
        return await self._run_sync(_get_path_creation_date, path)

    async def _run_sync(
        self,
        fun: Callable[Concatenate[Session, _P], _T],
        *args: _P.args,
        **kwargs: _P.kwargs
    ) -> _T:
        return await self.parent_session._run_sync(fun, *args, **kwargs)


@attrs.frozen
class AsyncSQLSequenceCollection(AsyncSequenceCollection):
    parent_session: AsyncSQLExperimentSession
    serializer: Serializer

    async def is_sequence(
        self, path: PureSequencePath
    ) -> Result[bool, PathNotFoundError]:
        return await self._run_sync(_is_sequence, path)

    async def get_stats(
        self, path: PureSequencePath
    ) -> Result[SequenceStats, PathNotFoundError | PathIsNotSequenceError]:
        return await self._run_sync(_get_stats, path)

    async def get_time_lanes(self, path: PureSequencePath) -> TimeLanes:
        return await self._run_sync(_get_time_lanes, path, self.serializer)

    async def get_global_parameters(self, path: PureSequencePath) -> ParameterNamespace:
        return await self._run_sync(_get_sequence_global_parameters, path)

    async def get_iteration_configuration(
        self, path: PureSequencePath
    ) -> IterationConfiguration:
        return await self._run_sync(_get_iteration_configuration, path, self.serializer)

    async def get_shots(
        self, path: PureSequencePath
    ) -> Result[list[PureShot], PathNotFoundError | PathIsNotSequenceError]:
        return await self._run_sync(_get_shots, path)

    async def get_shot_parameters(
        self, path: PureSequencePath, shot_index: int
    ) -> Mapping[DottedVariableName, Parameter]:
        return await self._run_sync(_get_shot_parameters, path, shot_index)

    async def get_all_shot_data(
        self, path: PureSequencePath, shot_index: int
    ) -> Mapping[DataLabel, Data]:
        return await self._run_sync(_get_all_shot_data, path, shot_index)

    async def get_shot_data_by_label(
        self, path: PureSequencePath, shot_index: int, data_label: DataLabel
    ) -> Data:
        return await self._run_sync(
            _get_shot_data_by_label, path, shot_index, data_label
        )

    async def get_shot_start_time(
        self, path: PureSequencePath, shot_index: int
    ) -> datetime:
        return await self._run_sync(_get_shot_start_time, path, shot_index)

    async def get_shot_end_time(
        self, path: PureSequencePath, shot_index: int
    ) -> datetime:
        return await self._run_sync(_get_shot_end_time, path, shot_index)

    async def _run_sync(
        self,
        fun: Callable[Concatenate[Session, _P], _T],
        *args: _P.args,
        **kwargs: _P.kwargs
    ) -> _T:
        return await self.parent_session._run_sync(fun, *args, **kwargs)
