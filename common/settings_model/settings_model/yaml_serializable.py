import abc
import pprint
from enum import Enum
from pathlib import Path, WindowsPath
from typing import Type, Self, TypeVar

import yaml
from pydantic import SecretStr, PostgresDsn
from pydantic.color import Color

from util import attrs
from .version import Version

yaml.SafeDumper.ignore_aliases = lambda *args: True

YamlNode = TypeVar("YamlNode", bound=yaml.Node)

_C = TypeVar("_C", bound=attrs.AttrsInstance)


class YAMLSerializable(abc.ABC):
    """
    Provide an interface for object that can be (de)serialized to yaml strings
    """

    def __init_subclass__(cls):
        """Register subclasses for serialization and deserialization to yaml"""
        cls.get_dumper().add_representer(cls, cls.representer)
        cls.get_loader().add_constructor(f"!{cls.__name__}", cls.constructor)

    @classmethod
    def register_attrs_class(cls, other_cls: type[_C]):
        fields = attrs.fields(other_cls)

        # fields that are not init are not serialized by default
        fields = [field for field in fields if field.init]

        def representer(dumper: yaml.Dumper, instance: _C):
            return dumper.represent_mapping(
                f"!{other_cls.__name__}",
                {field.name: getattr(instance, field.name) for field in fields},
            )

        cls.get_dumper().add_representer(other_cls, representer)

        def constructor(loader: yaml.Loader, node: yaml.Node) -> _C:
            kwargs = loader.construct_mapping(node, deep=True)

            try:
                return other_cls(**kwargs)
            except Exception as e:
                raise ValueError(
                    f"Could not construct {cls.__name__} from\n"
                    f" {pprint.pformat(kwargs)}"
                ) from e

        cls.get_loader().add_constructor(f"!{other_cls.__name__}", constructor)

    @classmethod
    def get_dumper(cls):
        return yaml.SafeDumper

    @classmethod
    def get_loader(cls):
        return yaml.SafeLoader

    @classmethod
    @abc.abstractmethod
    def representer(cls, dumper: yaml.Dumper, obj: Self) -> yaml.Node:
        """Represent a python object with a yaml string

        Overload this method in a child class to provide a yaml representation for a given type.
        """
        ...

    @classmethod
    @abc.abstractmethod
    def constructor(cls, loader: yaml.Loader, node: YamlNode) -> Self:
        """Build a python object from a YAML node

        Overload this method in a child class to provide a constructor for a given type from a yaml node.
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

        def constructor(loader: yaml.Loader, node: yaml.ScalarNode):
            scalar = loader.construct_scalar(node)
            if not isinstance(scalar, str):
                raise ValueError(f"Expected a string, got {type(scalar)}")
            return enum_class[scalar]

        cls.get_dumper().add_representer(enum_class, representer)
        cls.get_loader().add_constructor(f"!{enum_class.__name__}", constructor)

    def to_yaml(self) -> str:
        """Return a yaml string representing the object"""
        return YAMLSerializable.dump(self)

    def save_yaml(self, path: Path):
        """Save the serialized object to a yaml file"""
        serialized = self.to_yaml()
        with open(path, "w") as file:
            file.write(serialized)

    @classmethod
    def from_yaml(cls: Type[Self], serialized: str) -> Self:
        result = YAMLSerializable.load(serialized)
        if not isinstance(result, cls):
            raise ValueError(
                f"Cannot deserialized object of type {type(result)} to {cls.__name__}"
            )
        return result

    @classmethod
    def is_tag(cls, value: str):
        return value.startswith("!")


def tuple_representer(dumper: yaml.Dumper, value):
    return dumper.represent_sequence(r"!tuple", value)


def tuple_constructor(loader: yaml.Loader, node: yaml.SequenceNode):
    return tuple(loader.construct_sequence(node))


YAMLSerializable.get_dumper().add_representer(tuple, tuple_representer)
YAMLSerializable.get_loader().add_constructor(f"!tuple", tuple_constructor)


def path_representer(dumper: yaml.Dumper, path: Path):
    return dumper.represent_scalar("!Path", str(path))


YAMLSerializable.get_dumper().add_representer(Path, path_representer)
YAMLSerializable.get_dumper().add_representer(WindowsPath, path_representer)


def path_constructor(loader: yaml.Loader, node: yaml.ScalarNode):
    value = loader.construct_scalar(node)
    if not isinstance(value, str):
        raise ValueError(f"Expected a string, got {type(value)}")
    return Path(value)


YAMLSerializable.get_loader().add_constructor(f"!Path", path_constructor)


def color_representer(dumper: yaml.Dumper, color: Color):
    return dumper.represent_data(color.original())


YAMLSerializable.get_dumper().add_representer(Color, color_representer)


def database_url_representer(dumper: yaml.Dumper, url: PostgresDsn):
    return dumper.represent_data(str(url))


YAMLSerializable.get_dumper().add_representer(PostgresDsn, database_url_representer)


def secret_str_representer(dumper: yaml.Dumper, secret: SecretStr):
    return dumper.represent_data(secret.get_secret_value())


YAMLSerializable.get_dumper().add_representer(SecretStr, secret_str_representer)


def version_representer(dumper: yaml.Dumper, version: Version):
    return dumper.represent_data(str(version))


YAMLSerializable.get_dumper().add_representer(Version, version_representer)
