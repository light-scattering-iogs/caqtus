from typing import Optional

import yaml

from sequence.configuration.steps.step import Step
from settings_model import YAMLSerializable
from util import attrs, serialization

ShotName = str


@attrs.define
class ExecuteShot(Step):
    """Represents a step that executes a shot on the machine."""

    name: ShotName = attrs.field(
        converter=str,
        on_setattr=attrs.setters.convert,
    )

    def __init__(self, name: ShotName):
        super().__init__()
        self.name = name

    def __str__(self):
        return f"Do {self.name}"

    def __eq__(self, other):
        if not isinstance(other, ExecuteShot):
            return NotImplemented
        return self.name == other.name

    def expected_number_shots(self) -> Optional[int]:
        return 1


def unstructure_hook(execute_shot: ExecuteShot):
    return {
        "name": str(execute_shot.name),
    }


serialization.register_unstructure_hook(ExecuteShot, unstructure_hook)


def structure_hook(data: dict[str, str], cls: type[ExecuteShot]) -> ExecuteShot:
    return ExecuteShot(
        name=data["name"],
    )


serialization.register_structure_hook(ExecuteShot, structure_hook)


def representer(dumper: yaml.Dumper, step: ExecuteShot):
    return dumper.represent_mapping(
        f"!{ExecuteShot.__name__}",
        {
            "name": step.name,
        },
    )


YAMLSerializable.get_dumper().add_representer(ExecuteShot, representer)


def constructor(loader: yaml.Loader, node: yaml.Node):
    mapping = loader.construct_mapping(node, deep=True)
    try:
        return ExecuteShot(**mapping)
    except Exception as e:
        raise ValueError(
            f"Cannot construct {ExecuteShot.__name__} from {mapping}"
        ) from e


YAMLSerializable.get_loader().add_constructor(f"!{ExecuteShot.__name__}", constructor)
