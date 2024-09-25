from collections.abc import Mapping
from typing import Optional

import anyio
import attrs

from caqtus.utils.serialization import JSON
from .procedures import Procedure, ProcedureName


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

    _cancel_scope: anyio.CancelScope = attrs.field()
