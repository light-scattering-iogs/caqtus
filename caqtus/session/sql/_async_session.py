from typing import Callable, Concatenate, TypeVar, ParamSpec

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ._experiment_session import _get_global_parameters, _set_global_parameters
from ._serializer import Serializer
from .. import ParameterNamespace
from ..async_session import AsyncExperimentSession
from ..experiment_session import ExperimentSessionNotActiveError

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
