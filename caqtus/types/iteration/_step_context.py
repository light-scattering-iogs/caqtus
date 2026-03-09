from collections.abc import Mapping
from copy import deepcopy
from typing import Generic, TypeVar, Self, Optional

from caqtus.types.variable_name import DottedVariableName
from .._parameter_namespace import VariableNamespace

T = TypeVar("T")


class StepContext(Generic[T]):
    """Immutable context that contains the variables of a given step."""

    def __init__(
        self, initial_variables: Optional[Mapping[DottedVariableName, T]] = None
    ) -> None:
        self._variables = VariableNamespace[T]()
        if initial_variables is not None:
            self._variables.update(dict(initial_variables))

    def clone(self) -> Self:
        return deepcopy(self)

    def update_variable(self, name: DottedVariableName, value: T) -> Self:
        clone = self.clone()
        clone._variables.update({name: value})
        return clone

    @property
    def variables(self) -> VariableNamespace[T]:
        return deepcopy(self._variables)
