from __future__ import annotations

from typing import NewType, Protocol

import attrs

from caqtus.experiment_control._kernel import ExperimentKernel
from caqtus.utils._result import Failure, Success
from caqtus.utils.serialization import JSON

ProcedureName = NewType("ProcedureName", str)


class Procedure(Protocol):
    """Represents a procedure that can be run on the setup.

    A procedure is an async function that takes some arguments, run some sequences and
    analysis on the setup and
    """

    async def __call__(
        self, kernel: ExperimentKernel, *args: JSON, **kwargs: JSON
    ) -> Success[None] | Failure[Error]:
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


@attrs.frozen
class Error:
    """Represents an error that occurred during the execution of a procedure.

    Attributes:
        code: The error code.
            Values between -32768 and -32000 are reserved for pre-defined errors.
        message: The error message.
        data: Additional data that can help to understand the error.
    """

    code: int = attrs.field()
    message: str = attrs.field()
    data: JSON = attrs.field(factory=dict)
