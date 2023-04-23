from typing import Optional, Self

import yaml
from anytree import RenderTree

from settings_model import YAMLSerializable, validate_arguments
from .step import Step, compute_total_number_shots


class SequenceSteps(Step, YAMLSerializable):
    @validate_arguments
    def __init__(
        self, parent: Optional[Step] = None, children: Optional[list[Step]] = None
    ):
        super().__init__(parent, children)

    @classmethod
    def representer(cls, dumper: yaml.Dumper, step: Self):
        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {"children": [child for child in step.children]},
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        mapping = loader.construct_mapping(node, deep=True)
        try:
            return cls(**mapping)
        except Exception as e:
            raise ValueError(f"Cannot construct {cls.__name__} from {mapping}") from e

    def __repr__(self):
        return f"SequenceSteps(parent={self.parent}, children={self.children})"

    def __str__(self):
        return "\n".join(
            f"{pre}{node if not node is self else 'steps'}"
            for pre, _, node in RenderTree(self)
        )

    def __eq__(self, other):
        if not isinstance(other, SequenceSteps):
            return False
        return self.children == other.children

    def expected_number_shots(self) -> Optional[int]:
        return compute_total_number_shots(self.children)
