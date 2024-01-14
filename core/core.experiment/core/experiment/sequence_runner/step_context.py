from copy import deepcopy
from typing import Generic, TypeVar, Self

from core.compilation import VariableNamespace
from core.types.variable_name import DottedVariableName

T = TypeVar("T")


class StepContext(Generic[T]):
    """Immutable context that contains the variables of a given step."""

    def __init__(self) -> None:
        self._variables = VariableNamespace[T]()

    def clone(self) -> Self:
        return deepcopy(self)

    def update_variable(self, name: DottedVariableName, value: T) -> Self:
        clone = self.clone()
        clone._variables.update({name: value})
        return clone

    @property
    def variables(self):
        return deepcopy(self._variables)
