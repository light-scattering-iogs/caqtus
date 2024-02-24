from __future__ import annotations

from collections.abc import Iterable, Sequence, Mapping
from typing import Union, Any, Self

from core.types.expression import Expression
from core.types.variable_name import DottedVariableName
from util import serialization


class ParameterNamespace:
    """A nested namespace of parameters."""

    def __init__(
        self,
        content: Sequence[tuple[DottedVariableName, Expression | ParameterNamespace]],
    ) -> None:
        self._content = list(content)

    @classmethod
    def from_mapping(cls, content: Mapping[str, Any]) -> Self:
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
        return cls([(DottedVariableName(key), value) for key, value in content.items()])

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


def union_structure_hook(value, _) -> Expression | ParameterNamespace:
    if isinstance(value, str):
        return Expression(value)
    elif isinstance(value, list):
        return serialization.structure(value, ParameterNamespace)
    else:
        raise ValueError(f"Invalid value {value}")


serialization.register_structure_hook(
    Union["ParameterNamespace", Expression], union_structure_hook
)


def unstructure_hook(value: ParameterNamespace):
    serialization.unstructure(list(value.items()))


serialization.register_unstructure_hook(ParameterNamespace, unstructure_hook)


def structure_hook(value: Any, _) -> ParameterNamespace:
    content = serialization.structure(
        value, list[tuple[DottedVariableName, Expression]]
    )
    return ParameterNamespace(content)


serialization.register_structure_hook(ParameterNamespace, structure_hook)
