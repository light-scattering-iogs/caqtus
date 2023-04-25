from typing import Optional, Self

import yaml

from expression import Expression
from settings_model import YAMLSerializable, validate_arguments
from variable.name import DottedVariableName
from .step import Step, compute_total_number_shots


class LinspaceLoop(Step, YAMLSerializable):
    def __init__(
        self,
        name: DottedVariableName,
        start: Expression,
        stop: Expression,
        num: int,
        parent: Optional[Step] = None,
        children: Optional[list[Step]] = None,
    ):
        self.name = name
        self.start = start
        self.stop = stop
        self.num = num
        if not children:
            children = []
        Step.__init__(self, parent, children)

    @property
    def name(self):
        return self._name

    @name.setter
    @validate_arguments
    def name(self, value: DottedVariableName):
        self._name = value

    @property
    def start(self):
        return self._start

    @start.setter
    @validate_arguments
    def start(self, value: Expression):
        self._start = value

    @property
    def stop(self):
        return self._stop

    @stop.setter
    @validate_arguments
    def stop(self, value: Expression):
        self._stop = value

    @property
    def num(self):
        return self._num

    @num.setter
    @validate_arguments
    def num(self, value: int):
        self._num = value

    @classmethod
    def representer(cls, dumper: yaml.Dumper, step: Self):
        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {
                "name": step.name,
                "start": step.start,
                "stop": step.stop,
                "num": step.num,
                "children": [child for child in step.children],
            },
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        mapping = loader.construct_mapping(node, deep=True)
        try:
            return cls(**mapping)
        except Exception as e:
            raise ValueError(f"Cannot construct {cls.__name__} from {mapping}") from e

    def __str__(self):
        return (
            f"For {self.name} = {self.start.body} to {self.stop.body} with"
            f" {self.num} steps"
        )

    def __eq__(self, other):
        if not isinstance(other, LinspaceLoop):
            return False
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
