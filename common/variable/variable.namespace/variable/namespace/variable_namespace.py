from collections.abc import Mapping
from typing import Optional, Self, Generic, TypeVar

from benedict import benedict  # type: ignore

from variable.name import DottedVariableName

T = TypeVar("T")


class VariableNamespace(Generic[T]):
    def __init__(self, initial_variables: Optional[Self] = None):
        self._dict: benedict = benedict()
        if initial_variables is not None:
            # noinspection PyProtectedMember
            self._dict = initial_variables._dict.clone()

    def update(self, values: dict[DottedVariableName, T]):
        for key, value in values.items():
            self._dict[str(key)] = value

    def to_flat_dict(self) -> dict[DottedVariableName, T]:
        return {
            DottedVariableName(name.replace("$", ".")): value
            for name, value in self._dict.flatten(separator="$").items()
        }

    def __getitem__(self, item: DottedVariableName) -> T:
        return self._dict[str(item)]

    def __contains__(self, item: DottedVariableName) -> bool:
        return str(item) in self._dict

    def __or__(
        self, other: Mapping[DottedVariableName, T]
    ) -> Mapping[DottedVariableName, T]:
        if isinstance(other, Mapping):
            new = self._dict.clone()
            for key, value in other.items():
                new[key] = value
            return new
        else:
            return NotImplemented

    def __repr__(self):
        return f"{self.__class__.__name__}({self._dict})"
