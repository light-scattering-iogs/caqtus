import abc
from enum import Enum
from pathlib import Path, WindowsPath
from typing import Type

import pydantic
import yaml
from pydantic import SecretStr
from pydantic.color import Color

yaml.SafeDumper.ignore_aliases = lambda *args: True


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
        if isinstance(stream, Path):
            with open(stream, "r") as file:
                return yaml.load(file, Loader=cls.get_loader())
        else:
            return yaml.load(stream, Loader=cls.get_loader())

    @classmethod
    def dump(cls, data, stream=None):
        """Dump the serialized data on the stream"""

        if isinstance(stream, Path):
            serialized = yaml.dump(data, Dumper=cls.get_dumper(), sort_keys=False)
            with open(stream, "w") as file:
                file.write(serialized)
        else:
            return yaml.dump(
                data, stream=stream, Dumper=cls.get_dumper(), sort_keys=False
            )

    @classmethod
    def register_enum(cls, enum_class: Type[Enum]):
        def representer(dumper: yaml.Dumper, value):
            return dumper.represent_scalar(f"!{enum_class.__name__}", value.name)

        def constructor(loader: yaml.Loader, node: yaml.Node):
            return enum_class[loader.construct_scalar(node)]

        cls.get_dumper().add_representer(enum_class, representer)
        cls.get_loader().add_constructor(f"!{enum_class.__name__}", constructor)

    def to_yaml(self) -> str:
        return YAMLSerializable.dump(self)

    @classmethod
    def from_yaml(cls, serialized: str):
        result = YAMLSerializable.load(serialized)
        if not isinstance(result, cls):
            raise ValueError(f"Cannot deserialized object of type {type(result)} to {cls.__name__}")
        return result


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
        validate_all = True

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


def color_representer(dumper: yaml.Dumper, color: Color):
    return dumper.represent_data(color.original())


YAMLSerializable.get_dumper().add_representer(Color, color_representer)


def secret_str_representer(dumper: yaml.Dumper, secret: SecretStr):
    return dumper.represent_data(secret.get_secret_value())


YAMLSerializable.get_dumper().add_representer(SecretStr, secret_str_representer)
