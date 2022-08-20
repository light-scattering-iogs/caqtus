import abc

import pydantic
import yaml
from pathlib import Path, WindowsPath


class SettingsModel(abc.ABC, pydantic.BaseModel):
    """Allows to store and load experiment configuration with type validation

    All instances of a subclass of this class can be (de)serialized (from) to yaml based
    on their fields (see pydantic). This is used for persistence and loading of
    experiment settings. If you need to add some parameters to the experiment manager,
    it is recommended to create a new subclass of this class.
    """

    class Config:
        validate_assignment = True

    def __init_subclass__(cls):
        """Register subclasses for serialization and deserialization to yaml"""
        yaml.SafeDumper.add_representer(cls, cls.representer)
        yaml.SafeLoader.add_constructor(f"!{cls.__name__}", cls.constructor)

    @classmethod
    def representer(cls, dumper: yaml.Dumper, settings: "SettingsModel"):
        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {field: getattr(settings, field) for field in cls.__fields__},
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        return cls(**loader.construct_mapping(node, deep=True))


def path_representer(dumper: yaml.Dumper, path: Path):
    return dumper.represent_scalar("!Path", str(path))
yaml.SafeDumper.add_representer(Path, path_representer)
yaml.SafeDumper.add_representer(WindowsPath, path_representer)


def path_constructor(loader: yaml.Loader, node: yaml.Node):
    return Path(loader.construct_scalar(node))
yaml.SafeLoader.add_constructor(f"!Path", path_constructor)
