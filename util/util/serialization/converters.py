from typing import Any, Callable, TypeVar

from cattrs.converters import Converter
from cattrs.preconf.json import make_converter as make_json_converter
from cattrs.preconf.pyyaml import make_converter as make_yaml_converter

unstruct_collection_overrides = {tuple: tuple}

T = TypeVar("T")

converters = {
    "json": make_json_converter(unstruct_collection_overrides=unstruct_collection_overrides),
    "yaml": make_yaml_converter(unstruct_collection_overrides=unstruct_collection_overrides),
    "unconfigured": Converter(unstruct_collection_overrides=unstruct_collection_overrides)
}


def unstructure(obj: Any, unstructure_as: Any = None):
    return converters["unconfigured"].unstructure(obj, unstructure_as=unstructure_as)


def structure(obj: Any, cls: Any = None):
    return converters["unconfigured"].structure(obj, cls)


def register_unstructure_hook(cls: Any, hook: Callable[[Any], Any]) -> None:
    """Register a class-to-primitive converter function for a class.

    The converter function should take an instance of the class and return
    its Python equivalent.
    """

    for converter in converters.values():
        converter.register_unstructure_hook(cls, hook)


def register_structure_hook(cls: Any, func: Callable[[Any, type[T]], T]) -> None:
    """Register a primitive-to-class converter function for a type.

    The converter function should take two arguments:
      * a Python object to be converted,
      * the type to convert to

    and return the instance of the class. The type may seem redundant, but
    is sometimes needed (for example, when dealing with generic classes).
    """

    for converter in converters.values():
        converter.register_structure_hook(cls, func)
