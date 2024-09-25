from typing import NewType, Protocol

from caqtus.utils.serialization import JSON
from ._kernel import ExperimentKernel

ProcedureName = NewType("ProcedureName", str)


class Procedure(Protocol):
    """Represents a procedure that can be run on the setup.

    A procedure is an async function that takes some arguments, run some sequences and
    analysis on the setup and
    """

    async def __call__(
        self, kernel: ExperimentKernel, *args: JSON, **kwargs: JSON
    ) -> None:
        """Run the procedure on the setup.

        Args:
            kernel: The experiment kernel that gives access to the setup.
            *args: The parameters of the procedure. They must be JSON serializable.
            **kwargs: The parameters of the procedure. They must be JSON serializable.
        """

        ...
