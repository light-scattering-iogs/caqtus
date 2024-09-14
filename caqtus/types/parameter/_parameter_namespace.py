from __future__ import annotations

from collections.abc import Iterable, Sequence, Mapping
from typing import Union, Any, Self

from caqtus.formatter import fmt
from caqtus.types.expression import Expression
from caqtus.types.variable_name import DottedVariableName
from caqtus.utils import serialization
from ._parameter import Parameter, is_parameter

MappingNamespace = Mapping[
    str | DottedVariableName, Union[Expression, "MappingNamespace"]
]


class ParameterNamespace:
    """A nested namespace of user parameters.

    Objects of this class map from a variable name of type
    :py:class:`DottedVariableName` to either an unevaluated expression
    (:py:class:`Expression`) or another :py:class:`ParameterNamespace`.

    Objects of this class are not per-say a mapping, because the variable names have a
    definition order and can be duplicates.
    """

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
        """Return an iterable of flat key-value pairs in the namespace.

        The values are iterated over in their definition order in the namespace.
        """

        for key, value in self._content:
            if isinstance(value, ParameterNamespace):
                for sub_key, sub_value in value.flatten():
                    k = DottedVariableName.from_individual_names(
                        key.individual_names + sub_key.individual_names
                    )
                    yield k, sub_value
            else:
                yield key, value

    def get(self, parameter: DottedVariableName) -> Expression:
        """Return the expression associated with a parameter name.

        In case the parameter is defined several times in the namespace, it will return
        the last definition.

        Raises:
            KeyError, if the parameter is not present in the namespace.
        """

        for name, expression in reversed(list(self.flatten())):
            if name == parameter:
                return expression
        raise KeyError(parameter)

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

    def __getitem__(self, item: int) -> Expression | Self:
        return self._content[item][1]

    def __setitem__(self, item: int, value: Expression | Self) -> None:
        self._content[item] = (self._content[item][0], value)

    def __delitem__(self, item: int) -> None:
        del self._content[item]

    def evaluate(self) -> dict[DottedVariableName, Parameter]:
        """Evaluate the values in the namespace.

        Each expression is evaluated within the context of the parameters evaluated
        before.
        If two declarations have the same parameter name, the last value will overwrite
        the first one.
        """

        results: dict[DottedVariableName, Parameter] = {}
        for name, expression in self.flatten():
            value = expression.evaluate(results)
            if not is_parameter(value):
                raise TypeError(
                    fmt(
                        "{:expression}> for {:parameter}> does not "
                        "evaluate to a valid parameter type, got {:type}.",
                        expression,
                        name,
                        type(value),
                    )
                )
            results[name] = value

        return results

    def replace(self, parameter: DottedVariableName, expression: Expression) -> None:
        """Replace all occurrences of the parameter with the given value."""

        parameter_parts = parameter.individual_names

        for index, (name, value) in enumerate(self._content):
            name_parts = name.individual_names
            if len(name_parts) > len(parameter_parts):
                continue
            if parameter_parts[: len(name_parts)] == name_parts:
                remainder = parameter_parts[len(name_parts) :]
                if remainder:
                    if isinstance(value, ParameterNamespace):
                        value.replace(
                            DottedVariableName.from_individual_names(remainder),
                            expression,
                        )
                else:
                    self._content[index] = (name, expression)

    def names(self) -> set[DottedVariableName]:
        """Return the names of the parameters in the namespace."""

        return {name for name, _ in self.flatten()}


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
