from copy import deepcopy
from typing import Generic, TypeVar, Self, Optional

from core.configuration import DottedVariableName
from ..variable_namespace import VariableNamespace

T = TypeVar("T")


class StepContext(Generic[T]):
    """Immutable context that contains the variables of a given step.

    This object contains the value of some variables, and it also contains the previous value of the variables since the
    last time this object history was reset.
    """

    def __init__(self) -> None:
        self._variables = VariableNamespace[T]()

        # This is a dictionary of variables that have changed since the last time this object was reset.
        # The key is the variable name, and the value is the previous value of the variable.
        self._variables_that_changed: dict[DottedVariableName, Optional[T]] = {}

    def clone(self) -> Self:
        return deepcopy(self)

    def update_variable(self, name: DottedVariableName, value: T) -> Self:
        clone = self.clone()
        if name in clone._variables_that_changed:
            # We keep the last previous value as the correct previous value
            pass
        else:
            if name in clone._variables:
                if clone._variables[name] == value:
                    # No need to register the change if the value is the same
                    pass
                else:
                    clone._variables_that_changed[name] = clone._variables[name]
            else:
                clone._variables_that_changed[name] = None
        clone._variables.update({name: value})
        return clone

    def reset_history(self) -> Self:
        clone = self.clone()
        clone._variables_that_changed = {}
        return clone

    @property
    def variables(self):
        return deepcopy(self._variables)

    @property
    def updated_variables(self) -> set[DottedVariableName]:
        return set(self._variables_that_changed.keys())
