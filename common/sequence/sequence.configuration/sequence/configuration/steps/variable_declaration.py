from typing import Optional, Self

import yaml

from expression import Expression
from settings_model import YAMLSerializable
from util import attrs
from variable.name import DottedVariableName
from .step import Step


@attrs.define
class VariableDeclaration(Step):
    """Represents a step that declares or overwrite a variable."""

    name: DottedVariableName = attrs.field(
        validator=attrs.validators.instance_of(DottedVariableName),
        on_setattr=attrs.setters.validate,
    )
    expression: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )

    def __init__(
        self,
        name: DottedVariableName,
        expression: Expression,
        parent: Optional[Self] = None,
    ):
        self.__attrs_init__(name, expression)
        super().__init__(parent, None)

    def __repr__(self):
        return f"VariableDeclaration({self.name}, {self.expression})"

    def __str__(self):
        return f"{self.name} = {self.expression.body}"

    def __eq__(self, other):
        if not isinstance(other, VariableDeclaration):
            return NotImplemented
        return self.name == other.name and self.expression == other.expression

    def expected_number_shots(self) -> Optional[int]:
        return 0


def representer(dumper: yaml.Dumper, step: VariableDeclaration):
    return dumper.represent_mapping(
        f"!{VariableDeclaration.__name__}",
        {
            "name": step.name,
            "expression": step.expression,
        },
    )


YAMLSerializable.get_dumper().add_representer(VariableDeclaration, representer)


def constructor(loader: yaml.Loader, node: yaml.Node):
    mapping = loader.construct_mapping(node, deep=True)
    try:
        return VariableDeclaration(**mapping)
    except Exception as e:
        raise ValueError(
            f"Cannot construct {VariableDeclaration.__name__} from {mapping}"
        ) from e


YAMLSerializable.get_loader().add_constructor(
    f"!{VariableDeclaration.__name__}", constructor
)
