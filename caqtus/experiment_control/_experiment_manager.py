from __future__ import annotations

from collections.abc import Mapping
from typing import Optional

import anyio
import attrs

from caqtus.utils.serialization import JSON
from ._error import Error
from .procedures import Procedure, ProcedureName, ProcedureError
from ..utils._result import Success, Failure


class ExperimentManager:
    """Controls an experiment and schedule procedures to run on the setup.

    There should only be at most one experiment manager per setup since it is in charge
    of ensuring that only once procedure can run at a time.

    Args:
        available_procedures: The procedures that can be run on the setup.
            Only procedures that are listed here can be selected to run.
    """

    def __init__(self, available_procedures: Mapping[ProcedureName, Procedure]):
        self._available_procedures = available_procedures
        self._currently_running_procedure: Optional[RunningProcedure] = None

    async def run_procedure(
        self, procedure_name: ProcedureName, *args: JSON, **kwargs: JSON
    ) -> (
        Success[None]
        | Failure[NoSuchProcedureError]
        | Failure[ProcedureAlreadyRunningError]
        | Failure[ProcedureInterruptedError]
        | Failure[ProcedureError]
    ):
        """Run a procedure on the setup.

        Args:
            procedure_name: The name of the procedure to run.
            *args: The arguments to pass to the procedure.
            **kwargs: The keyword arguments to pass to the procedure.
        """

        procedure = self._available_procedures.get(procedure_name)
        if procedure is None:
            return Failure(NoSuchProcedureError(procedure_name))

        if self._currently_running_procedure is not None:
            return Failure(
                ProcedureAlreadyRunningError(
                    running_procedure=self._currently_running_procedure.procedure_name,
                    to_run_procedure=procedure_name,
                )
            )

        with anyio.CancelScope() as cancel_scope:
            self._currently_running_procedure = RunningProcedure(
                procedure_name=procedure_name,
                args=args,
                kwargs=kwargs,
                cancel_scope=cancel_scope,
            )

            result = await procedure(*args, **kwargs)
            return result
        return ProcedureInterruptedError(procedure_name)


@attrs.frozen
class RunningProcedure:
    """Represents a procedure that is currently running on the setup.

    Attributes:
        procedure_name: The name of the procedure that is running.
        args: The arguments that were passed to the procedure.
        kwargs: The keyword arguments that were passed to the procedure.
    """

    procedure_name: ProcedureName = attrs.field()
    args: tuple[JSON, ...] = attrs.field()
    kwargs: dict[str, JSON] = attrs.field()
    cancel_scope: anyio.CancelScope = attrs.field()


class ProcedureAlreadyRunningError(Error):
    """Error when trying to run a procedure while another one is already running."""

    def __init__(
        self, running_procedure: ProcedureName, to_run_procedure: ProcedureName
    ):
        super().__init__(
            code=-1000,
            message="A procedure is already running.",
            data={
                "running_procedure": running_procedure,
                "to_run_procedure": to_run_procedure,
            },
        )


class NoSuchProcedureError(Error):
    """Error when trying to run a procedure that does not exist."""

    def __init__(self, procedure_name: ProcedureName):
        super().__init__(
            code=-1001,
            message="The procedure does not exist.",
            data={"procedure_name": procedure_name},
        )


class ProcedureInterruptedError(Error):
    """Error when a procedure is interrupted."""

    def __init__(self, procedure_name: ProcedureName):
        super().__init__(
            code=-1002,
            message="The procedure was interrupted.",
            data={"procedure_name": procedure_name},
        )
