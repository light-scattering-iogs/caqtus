import inspect
import logging
import pprint
from abc import ABC
from functools import cached_property
from typing import Self, ClassVar, no_type_check

import pydantic
import yaml
from pydantic import validator

from .version import Version
from .yaml_serializable import YAMLSerializable

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class BaseModel(pydantic.BaseModel):
    @no_type_check
    def __setattr__(self, name, value):
        """
        To be able to use properties with setters
        """
        try:
            super().__setattr__(name, value)
        except ValueError as e:
            setters = inspect.getmembers(
                self.__class__,
                predicate=lambda x: isinstance(x, property) and x.fset is not None,
            )
            for setter_name, func in setters:
                if setter_name == name:
                    object.__setattr__(self, name, value)
                    break
            else:
                raise e


class SettingsModel(YAMLSerializable, BaseModel, ABC):
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
        keep_untouched = (cached_property,)

    @classmethod
    def representer(cls, dumper: yaml.Dumper, settings: Self):
        """Represent a python object with a yaml string

        Overload this method in a child class to change the default representation.
        """

        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {field: getattr(settings, field) for field in cls.__fields__},
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        """Build a python object from of dictionary of parameters

        Overload this method in a child class to change the default construction.
        """

        kwargs = loader.construct_mapping(node, deep=True)

        try:
            return cls(**kwargs)
        except Exception as e:
            raise ValueError(
                f"Could not construct {cls.__name__} from\n {pprint.pformat(kwargs)}"
            ) from e


class VersionedSettingsModel(SettingsModel, ABC):
    """A settings model that has a version number.

    When making non-backward compatible changes to a child class, the major version of
    this child class __version__ should be incremented. It is also necessary to overload
    the method 'update_parameters_version' that takes care of updating the old stored
    parameters into the new format.

    Attributes:
        __version__: The current version of the class. When making non-backward
            compatible changes to a child class, the major version should be
            incremented.
        version: The version of the instance. When creating an instance, the methode
            'update_parameters_version' will be called to translate the parameters to be
             compatible with the current version.
    """

    __version__: ClassVar[str]
    version: Version

    def __init__(self, **kwargs):
        updated_kwargs = self.update_parameters_version(kwargs)
        super().__init__(**updated_kwargs)

    @validator("version")
    def validate_version(cls, version: Version):
        current_version = Version.parse(cls.__version__)
        if version.is_compatible(current_version):
            return version
        else:
            raise ValueError(
                f"Version {version} is not compatible with current version"
                f" {current_version} for {cls.__name__}"
            )

    @classmethod
    def update_parameters_version(cls, kwargs: dict) -> dict:
        """Update the parameters to be compatible with the current version of the class.

        The default implementation does nothing but set the version to 0.0.0 if it is
        not present in the parameters. This method should be overloaded in child
        classes.
        """

        if "version" not in kwargs:
            kwargs["version"] = Version(major=0, minor=0, patch=0)
        return kwargs
