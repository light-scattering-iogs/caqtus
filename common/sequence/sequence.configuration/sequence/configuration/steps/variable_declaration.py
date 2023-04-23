from typing import Optional, Self

import yaml

from expression import Expression
from settings_model import YAMLSerializable, validate_arguments
from variable.name import DottedVariableName
from .step import Step


class VariableDeclaration(Step, YAMLSerializable):
    def __init__(
        self,
        name: DottedVariableName,
        expression: Expression,
        parent: Optional[Self] = None,
    ):
        self.name = name
        self.expression = expression
        Step.__init__(self, parent, None)

    @property
    def name(self):
        return self._name

    @name.setter
    @validate_arguments
    def name(self, value: DottedVariableName):
        self._name = value

    @property
    def expression(self):
        return self._expression

    @expression.setter
    @validate_arguments
    def expression(self, value: Expression):
        self._expression = value

    @classmethod
    def representer(cls, dumper: yaml.Dumper, step: Self):
        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {
                "name": step.name,
                "expression": step.expression,
            },
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        mapping = loader.construct_mapping(node, deep=True)
        try:
            return cls(**mapping)
        except Exception as e:
            raise ValueError(f"Cannot construct {cls.__name__} from {mapping}") from e

    def __repr__(self):
        return f"VariableDeclaration({self.name}, {self.expression})"

    def __str__(self):
        return f"{self.name} = {self.expression.body}"

    def __eq__(self, other):
        if not isinstance(other, VariableDeclaration):
            return False
        return self.name == other.name and self.expression == other.expression

    def expected_number_shots(self) -> Optional[int]:
        return 0
