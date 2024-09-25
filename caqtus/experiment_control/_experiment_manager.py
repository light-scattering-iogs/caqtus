from collections.abc import Mapping

from .procedures import Procedure, ProcedureName


class ExperimentManager:
    """Controls an experiment and schedule procedures to run on the setup.

    There should only be at most one experiment manager per setup since it is in charge
    of ensuring that only once procedure can run at a time.
    """

    def __init__(self, available_procedures: Mapping[ProcedureName, Procedure]):
        self._current_procedure = None
