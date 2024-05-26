import contextlib
from typing import Protocol

from caqtus.types.parameter import ParameterNamespace
from .path_hierarchy import AsyncPathHierarchy
from .sequence_collection import AsyncSequenceCollection


class AsyncExperimentSession(
    contextlib.AbstractAsyncContextManager["AsyncExperimentSession"], Protocol
):
    """Asynchronous version of ExperimentSession.

    For a detailed description of the methods, see ExperimentSession.
    This session cannot be used in several tasks concurrently, it must be used
    sequentially.
    """

    paths: AsyncPathHierarchy
    sequences: AsyncSequenceCollection

    async def get_global_parameters(self) -> ParameterNamespace: ...

    async def set_global_parameters(self, parameters: ParameterNamespace) -> None: ...
