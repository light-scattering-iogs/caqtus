from typing import Optional, Self

import yaml

from sequence.configuration.steps.step import Step
from settings_model import YAMLSerializable, validate_arguments

ShotName = str


class ExecuteShot(Step, YAMLSerializable):
    @validate_arguments
    def __init__(self, name: ShotName, parent: Optional[Step] = None):
        self.name = name
        Step.__init__(self, parent, None)

    def __str__(self):
        return f"Do {self.name}"

    def __eq__(self, other):
        if not isinstance(other, ExecuteShot):
            return False
        return self.name == other.name

    @classmethod
    def representer(cls, dumper: yaml.Dumper, step: Self):
        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {
                "name": step.name,
            },
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        mapping = loader.construct_mapping(node, deep=True)
        try:
            return cls(**mapping)
        except Exception as e:
            raise ValueError(f"Cannot construct {cls.__name__} from {mapping}") from e

    def expected_number_shots(self) -> Optional[int]:
        return 1
