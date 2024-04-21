import contextlib
from typing import Protocol

from caqtus.session import ParameterNamespace


class AsyncExperimentSession(contextlib.AbstractAsyncContextManager, Protocol):
    """Asynchronous version of ExperimentSession.

    For a detailed description of the methods, see ExperimentSession.
    """

    async def get_global_parameters(self) -> ParameterNamespace: ...

    async def set_global_parameters(self, parameters: ParameterNamespace) -> None: ...
