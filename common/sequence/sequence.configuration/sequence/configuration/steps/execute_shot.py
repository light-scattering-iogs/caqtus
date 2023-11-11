from typing import Optional

import yaml

from sequence.configuration.steps.step import Step
from settings_model import YAMLSerializable

ShotName = str


class ExecuteShot(Step):
    """Represents a step that executes a shot on the machine."""

    def __init__(self, name: ShotName, parent: Optional[Step] = None):
        if not isinstance(name, ShotName):
            raise TypeError(f"Expected <str> for name, got {type(name)}")
        self.name = name
        super().__init__(parent, None)

    def __str__(self):
        return f"Do {self.name}"

    def __eq__(self, other):
        if not isinstance(other, ExecuteShot):
            return NotImplemented
        return self.name == other.name

    def expected_number_shots(self) -> Optional[int]:
        return 1


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
