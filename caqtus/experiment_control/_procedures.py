from typing import NewType, Protocol

from caqtus.utils.serialization import JSON
from ._kernel import ExperimentKernel

ProcedureName = NewType("ProcedureName", str)


class Procedure(Protocol):
    """Represents a procedure that can be run on the setup.

    A procedure is an async function that takes some arguments, run some sequences and
    analysis on the setup and

    The first argument of the procedure is the experiment kernel that gives access to
    the setup. The rest of the arguments are the parameters of the procedure.
    """

    async def __call__(
        self, kernel: ExperimentKernel, *args: JSON, **kwargs: JSON
    ) -> None: ...
