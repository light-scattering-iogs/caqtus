from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Self, Any

from settings_model import yaml, YAMLSerializable
from util import attrs

NAME_REGEX = re.compile(r"^[^\W\d]\w*$")


@attrs.define
class DottedVariableName(YAMLSerializable):
    _dotted_name: str
    _individual_names: tuple[VariableName, ...] = attrs.field(init=False, repr=False)

    def __init__(self, dotted_name: str):
        names = tuple(dotted_name.split("."))
        self._individual_names = tuple(VariableName(name) for name in names)
        self._dotted_name = str(dotted_name)

    @property
    def dotted_name(self) -> str:
        return self._dotted_name

    @property
    def individual_names(self) -> tuple[VariableName, ...]:
        return self._individual_names

    @classmethod
    def from_individual_names(cls, names: Iterable[VariableName]) -> Self:
        return cls(".".join(str(name) for name in names))

    @classmethod
    def representer(cls, dumper: yaml.Dumper, obj: Self) -> yaml.Node:
        return dumper.represent_scalar(f"!{cls.__name__}", str(obj))

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node) -> Self:
        if not isinstance(node, yaml.ScalarNode):
            raise ValueError(f"Expected a scalar node, got {type(node)}")
        return cls(loader.construct_scalar(node))

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value) -> Self:
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls(value)
        raise ValueError(f"Invalid variable name: {value}")

    def __str__(self) -> str:
        return self._dotted_name

    def __repr__(self):
        return f"{type(self).__name__}('{self._dotted_name}')"

    def __hash__(self):
        return hash(self._dotted_name)

    def __eq__(self, other):
        if isinstance(other, DottedVariableName):
            return self._dotted_name == other._dotted_name
        else:
            return NotImplemented


def dotted_variable_name_converter(name: Any) -> DottedVariableName:
    if isinstance(name, DottedVariableName):
        return name
    elif isinstance(name, str):
        return DottedVariableName(name)
    else:
        raise ValueError(f"Invalid variable name: {name}")


@attrs.define
class VariableName(DottedVariableName):
    def __init__(self, name: str):
        if not NAME_REGEX.match(name):
            raise ValueError(f"Invalid variable name: {name}")
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
        else:
            return NotImplemented
