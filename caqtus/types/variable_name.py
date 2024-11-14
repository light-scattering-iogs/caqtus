from __future__ import annotations

from collections.abc import Iterable
from typing import Self, Any

import attrs

from caqtus.utils import serialization


@attrs.define(repr=False, eq=False, init=False)
class DottedVariableName:
    """Represents the name of a parameter.

    Instances of this class represents the name of a parameter.
    They must be valid python identifiers, possibly separated by dots to represent
    a hierarchy of names.

    For example, the names "a", "foo.bar", and "a.b.c" are all valid names.
    """

    _dotted_name: str
    _individual_names: tuple[VariableName, ...] = attrs.field(init=False, repr=False)

    def __init__(self, dotted_name: str):
        names = tuple(dotted_name.split("."))
        self._individual_names = tuple(VariableName(name) for name in names)
        self._dotted_name = str(dotted_name)

    @property
    def dotted_name(self) -> str:
        """The string representation of the name."""

        return self._dotted_name

    @property
    def individual_names(self) -> tuple[VariableName, ...]:
        """The individual separated by dots that make up the identifier."""

        return self._individual_names

    @classmethod
    def from_individual_names(cls, names: Iterable[VariableName]) -> Self:
        """Create a new instance from an iterable of individual names."""

        return cls(".".join(str(name) for name in names))

    def __str__(self) -> str:
        return self._dotted_name

    def __repr__(self):
        return f"{type(self).__name__}('{self._dotted_name}')"

    def __hash__(self):
        return hash(self._dotted_name)

    def __eq__(self, other):
        if isinstance(other, DottedVariableName):
            return self._dotted_name == other._dotted_name
        elif isinstance(other, str):
            return self._dotted_name == other
        else:
            return NotImplemented


def dotted_variable_name_converter(name: Any) -> DottedVariableName:
    if isinstance(name, DottedVariableName):
        return name
    elif isinstance(name, str):
        return DottedVariableName(name)
    else:
        raise InvalidVariableNameError(f"Invalid variable name: {name}")


@attrs.define(eq=False, repr=False, init=False)
class VariableName(DottedVariableName):
    """Represents a single variable name."""

    def __init__(self, name: str):
        if not name.isidentifier():
            raise InvalidVariableNameError(f"Invalid variable name: {name}")
        self._individual_names = (self,)
        self._dotted_name = str(name)

    def __hash__(self):
        return super().__hash__()

    def __repr__(self):
        return super().__repr__()

    def __str__(self):
        return super().__str__()

    def __eq__(self, other):
        if isinstance(other, VariableName):
            return self._dotted_name == other._dotted_name
        elif isinstance(other, str):
            return self._dotted_name == other
        else:
            return NotImplemented


def unstructure_hook(dotted_variable_name: DottedVariableName) -> str:
    return dotted_variable_name.dotted_name


serialization.register_unstructure_hook(DottedVariableName, unstructure_hook)


def structure_hook(data: str, cls: type[DottedVariableName]) -> DottedVariableName:
    return DottedVariableName(data)


serialization.register_structure_hook(DottedVariableName, structure_hook)


class InvalidVariableNameError(ValueError):
    pass
