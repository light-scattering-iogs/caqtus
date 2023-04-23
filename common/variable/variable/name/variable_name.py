import re
from collections import UserString
from collections.abc import Iterable
from typing import Self

import yaml

from settings_model import YAMLSerializable

NAME_REGEX = re.compile(r"^[^\W\d]\w*$")


class DottedVariableName(UserString, YAMLSerializable):
    def __init__(self, dotted_name: str):
        names = tuple(dotted_name.split("."))
        self._individual_names = tuple(VariableName(name) for name in names)
        super().__init__(dotted_name)

    @property
    def individual_names(self) -> tuple["VariableName", ...]:
        return self._individual_names

    @classmethod
    def from_individual_names(cls, names: Iterable["VariableName"]) -> Self:
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


class VariableName(DottedVariableName):
    def __init__(self, name: str):
        if not NAME_REGEX.match(name):
            raise ValueError(f"Invalid variable name: {name}")
        self._individual_names = (self,)
        UserString.__init__(self, name)
