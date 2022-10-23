import abc
from pathlib import Path, WindowsPath

import pydantic
import yaml


class YAMLSerializable(abc.ABC):
    """
    Provide a common class with YAML dumper and loader that is used for serialization
    """

    def __init_subclass__(cls):
        """Register subclasses for serialization and deserialization to yaml"""
        cls.get_dumper().add_representer(cls, cls.representer)
        cls.get_loader().add_constructor(f"!{cls.__name__}", cls.constructor)

    @classmethod
    def get_dumper(cls):
        return yaml.SafeDumper

    @classmethod
    def get_loader(cls):
        return yaml.SafeLoader

    @classmethod
    @abc.abstractmethod
    def representer(cls, dumper: yaml.Dumper, settings: "SettingsModel"):
        """Represent a python object with a yaml string

        Overload this method in a child class to give a representation.
        """
        ...

    @classmethod
    @abc.abstractmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        """Build a python object from a YAML node

        Overload this method in a child class to provide a constructor.
        """
        ...

    @classmethod
    def load(cls, stream):
        return yaml.load(stream, Loader=cls.get_loader())

    @classmethod
    def dump(cls, data, stream=None):
        return yaml.dump(data, stream=stream, Dumper=cls.get_dumper())


class SettingsModel(YAMLSerializable, pydantic.BaseModel, abc.ABC):
    """Allows to store and load experiment configuration with type validation

    All instances of a subclass of this class can be (de)serialized (from) to yaml based
    on their fields (see pydantic). This is used for persistence and loading of
    experiment settings. If you need to add some parameters to the experiment manager,
    it is recommended to create a new subclass of this class.
    """

    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True

    @classmethod
    def representer(cls, dumper: yaml.Dumper, settings: "SettingsModel"):
        """Represent a python object with a yaml string

        Overload this method in a child class to change the default representation.
        """
        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {field: getattr(settings, field) for field in cls.__fields__},
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        """Build a python object from a YAML node

        Overload this method in a child class to change the default construction.
        """
        return cls(**loader.construct_mapping(node, deep=True))


def path_representer(dumper: yaml.Dumper, path: Path):
    return dumper.represent_scalar("!Path", str(path))


YAMLSerializable.get_dumper().add_representer(Path, path_representer)
YAMLSerializable.get_dumper().add_representer(WindowsPath, path_representer)


def path_constructor(loader: yaml.Loader, node: yaml.Node):
    return Path(loader.construct_scalar(node))


YAMLSerializable.get_loader().add_constructor(f"!Path", path_constructor)
