from typing import Optional

import yaml

from expression import Expression
from settings_model import YAMLSerializable
from util import attrs
from variable.name import DottedVariableName
from .step import Step, compute_total_number_shots


@attrs.define
class LinspaceLoop(Step):
    """Represent a loop over a variable with a given number of steps."""

    name: DottedVariableName = attrs.field(
        validator=attrs.validators.instance_of(DottedVariableName),
        on_setattr=attrs.setters.validate,
    )
    start: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )
    stop: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )
    num: int = attrs.field(
        converter=int,
        on_setattr=attrs.setters.convert,
    )

    def __init__(
        self,
        name: DottedVariableName,
        start: Expression,
        stop: Expression,
        num: int,
        parent: Optional[Step] = None,
        children: Optional[list[Step]] = None,
    ):
        self.__attrs_init__(name, start, stop, num)
        if not children:
            children = []
        super().__init__(self, parent, children)

    def __str__(self):
        return (
            f"For {self.name} = {self.start.body} to {self.stop.body} with"
            f" {self.num} steps"
        )

    def __eq__(self, other):
        if not isinstance(other, LinspaceLoop):
            return NotImplemented
        return (
            self.name == other.name
            and self.start == other.start
            and self.stop == other.stop
            and self.num == other.num
            and self.children == other.children
        )

    def expected_number_shots(self) -> Optional[int]:
        number_sub_steps = compute_total_number_shots(self.children)
        if number_sub_steps is None:
            return None
        return self.num * number_sub_steps


def representer(dumper: yaml.Dumper, step: LinspaceLoop):
    return dumper.represent_mapping(
        f"!{LinspaceLoop.__name__}",
        {
            "name": step.name,
            "start": step.start,
            "stop": step.stop,
            "num": step.num,
            "children": [child for child in step.children],
        },
    )


YAMLSerializable.get_dumper().add_representer(LinspaceLoop, representer)


def constructor(loader: yaml.Loader, node: yaml.Node):
    mapping = loader.construct_mapping(node, deep=True)
    try:
        return LinspaceLoop(**mapping)
    except Exception as e:
        raise ValueError(
            f"Cannot construct {LinspaceLoop.__name__} from {mapping}"
        ) from e


YAMLSerializable.get_loader().add_constructor(f"!{LinspaceLoop.__name__}", constructor)
