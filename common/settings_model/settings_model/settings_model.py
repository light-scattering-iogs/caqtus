import abc
from .yaml_serializable import YAMLSerializable

import pydantic
import yaml


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
