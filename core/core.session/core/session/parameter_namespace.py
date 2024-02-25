from __future__ import annotations

from collections.abc import Iterable, Sequence, Mapping
from typing import Union, Any, Self

from core.types.expression import Expression
from core.types.variable_name import DottedVariableName
from util import serialization

MappingNamespace = Mapping[
    str | DottedVariableName, Union[Expression, "MappingNamespace"]
]


class ParameterNamespace:
    """A nested namespace of parameters."""

    def __init__(
        self,
        content: Sequence[tuple[DottedVariableName, Expression | Self]],
    ) -> None:
        for key, value in content:
            if not isinstance(key, DottedVariableName):
                raise ValueError(f"Invalid key {key}")
            if not isinstance(value, (Expression, ParameterNamespace)):
                raise ValueError(f"Invalid value {value}")
        self._content = list(content)

    @classmethod
    def from_mapping(cls, mapping: MappingNamespace) -> Self:
        """Construct a ParameterNamespace from a mapping of strings to values.

        Example:
            .. code-block:: python

                    namespace = ParameterNamespace.from_mapping({
                        "a": 1,
                        "b": {
                            "c": 2,
                            "d": 3,
                        },
                    })
        """

        content = []

        for key, value in mapping.items():
            if isinstance(key, str):
                k = DottedVariableName(key)
            elif isinstance(key, DottedVariableName):
                k = key
            else:
                raise TypeError(f"Invalid key {key}")
            if isinstance(value, Mapping):
                content.append((k, cls.from_mapping(value)))
            elif isinstance(value, Expression):
                content.append((k, value))
            else:
                raise TypeError(f"Invalid value {value}")

        return cls(content)

    @classmethod
    def empty(cls) -> Self:
        """Return an empty namespace."""

        return cls([])

    def items(
        self,
    ) -> Iterable[tuple[DottedVariableName, Expression | ParameterNamespace]]:
        """Return an iterable of the items in the namespace."""

        return iter(self._content)

    def flatten(self) -> Iterable[tuple[DottedVariableName, Expression]]:
        """Return an iterable of flat key-value pairs in the namespace."""

        for key, value in self._content:
            if isinstance(value, ParameterNamespace):
                for sub_key, sub_value in value.flatten():
                    k = DottedVariableName.from_individual_names(
                        key.individual_names + sub_key.individual_names
                    )
                    yield k, sub_value
            else:
                yield key, value

    def __repr__(self):
        return f"{self.__class__.__name__}({self._content})"

    def __eq__(self, other):
        """Return True if the other object is equal to this one.

        The comparison checks that both objects have the same flattened content.
        """
        if isinstance(other, ParameterNamespace):
            return list(self.flatten()) == list(other.flatten())
        else:
            return NotImplemented


def union_structure_hook(value, _) -> Expression | ParameterNamespace:
    if isinstance(value, str):
        return Expression(value)
    elif isinstance(value, list):
        return serialization.structure(value, ParameterNamespace)
    else:
        raise ValueError(f"Invalid value {value}")


serialization.register_structure_hook(
    Expression | ParameterNamespace, union_structure_hook
)


def unstructure_hook(value: ParameterNamespace):
    return serialization.unstructure(list(value.items()))


serialization.register_unstructure_hook(ParameterNamespace, unstructure_hook)


def structure_hook(value: Any, _) -> ParameterNamespace:
    content = serialization.structure(
        value, list[tuple[DottedVariableName, Expression | ParameterNamespace]]
    )
    return ParameterNamespace(content)


serialization.register_structure_hook(ParameterNamespace, structure_hook)
