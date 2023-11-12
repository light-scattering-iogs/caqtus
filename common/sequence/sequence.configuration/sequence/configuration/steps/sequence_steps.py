from collections.abc import Iterable
from typing import Optional

import yaml
from anytree import RenderTree

from settings_model import YAMLSerializable
from util import attrs, serialization
from .step import Step, compute_total_number_shots


@attrs.define
class SequenceSteps(Step):
    """Represents a list of sub-steps that are executed sequentially."""

    def __init__(
        self, parent: Optional[Step] = None, children: Optional[Iterable[Step]] = None
    ):
        super().__init__(parent=parent, children=children)

    def __repr__(self):
        return f"SequenceSteps(parent={self.parent}, children={self.children})"

    def __str__(self):
        return "\n".join(
            f"{pre}{node if not node is self else 'steps'}"
            for pre, _, node in RenderTree(self)
        )

    def __eq__(self, other):
        if not isinstance(other, SequenceSteps):
            return NotImplemented
        return self.children == other.children

    def expected_number_shots(self) -> Optional[int]:
        return compute_total_number_shots(self.children)


def unstructure_hook(sequence_steps: SequenceSteps) -> dict:
    return {
        "children": serialization.unstructure(
            sequence_steps.children, tuple[Step, ...]
        ),
    }


serialization.register_unstructure_hook(SequenceSteps, unstructure_hook)


def structure_hook(data: dict, cls: type[SequenceSteps]) -> SequenceSteps:
    return SequenceSteps(
        children=serialization.structure(data["children"], tuple[Step, ...])
    )


serialization.register_structure_hook(SequenceSteps, structure_hook)


def representer(dumper: yaml.Dumper, step: SequenceSteps):
    return dumper.represent_mapping(
        f"!{SequenceSteps.__name__}",
        {"children": [child for child in step.children]},
    )


YAMLSerializable.get_dumper().add_representer(SequenceSteps, representer)


def constructor(loader: yaml.Loader, node: yaml.Node):
    mapping = loader.construct_mapping(node, deep=True)
    try:
        return SequenceSteps(**mapping)
    except Exception as e:
        raise ValueError(
            f"Cannot construct {SequenceSteps.__name__} from {mapping}"
        ) from e


YAMLSerializable.get_loader().add_constructor(f"!{SequenceSteps.__name__}", constructor)
