import contextlib
from typing import Protocol

from caqtus.session import ParameterNamespace
from .path_hierarchy import AsyncPathHierarchy


class AsyncExperimentSession(
    contextlib.AbstractAsyncContextManager["AsyncExperimentSession"], Protocol
):
    """Asynchronous version of ExperimentSession.

    For a detailed description of the methods, see ExperimentSession.
    """

    paths: AsyncPathHierarchy

    async def get_global_parameters(self) -> ParameterNamespace: ...

    async def set_global_parameters(self, parameters: ParameterNamespace) -> None: ...
