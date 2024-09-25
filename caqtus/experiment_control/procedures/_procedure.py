from __future__ import annotations

from typing import NewType, Protocol

from caqtus.utils._result import Failure, Success
from caqtus.utils.serialization import JSON
from .._error import Error
from .._kernel import ExperimentKernel

ProcedureName = NewType("ProcedureName", str)


class Procedure(Protocol):
    """Represents a procedure that can be run on the setup."""

    async def __call__(
        self, kernel: ExperimentKernel, *args: JSON, **kwargs: JSON
    ) -> Success[None] | Failure[ProcedureError]:
        """Run the procedure on the setup.

        Args:
            kernel: The experiment kernel that gives access to the setup.
            *args: The parameters of the procedure. They must be JSON serializable.
            **kwargs: The parameters of the procedure. They must be JSON serializable.

        Returns:
            A success object with no value if the procedure was successful, otherwise a
            failure object containing the error that occurred.
        """

        ...


class ProcedureError(Error):
    """Represents an error that occurred during the execution of a procedure."""

    pass
