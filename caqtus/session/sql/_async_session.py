from datetime import datetime
from typing import Callable, Concatenate, TypeVar, ParamSpec

import attrs
from returns.result import Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ._experiment_session import _get_global_parameters, _set_global_parameters
from ._path_hierarchy import _does_path_exists, _get_children, _get_path_creation_date
from ._serializer import Serializer
from .. import ParameterNamespace, PureSequencePath
from ..async_session import AsyncExperimentSession, AsyncPathHierarchy
from ..experiment_session import ExperimentSessionNotActiveError
from ..path_hierarchy import PathNotFoundError, PathIsRootError
from ..sequence_collection import PathIsSequenceError

_T = TypeVar("_T")
_P = ParamSpec("_P")


class AsyncSQLExperimentSession(AsyncExperimentSession):
    def __init__(self, async_session: AsyncSession, serializer: Serializer):
        self._async_session = async_session
        self._is_active = False

    async def __aenter__(self):
        if self._is_active:
            raise RuntimeError("Session is already active")
        self._transaction = await self._async_session.begin().__aenter__()
        self._is_active = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._transaction.__aexit__(exc_type, exc_val, exc_tb)
        self._transaction = None
        self._is_active = False

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
        if not self._is_active:
            raise ExperimentSessionNotActiveError(
                "Experiment session was not activated"
            )
        return self._async_session


@attrs.frozen
class SQLPathHierarchy(AsyncPathHierarchy):
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
