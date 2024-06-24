from datetime import datetime
from typing import Any, Callable, TypeVar

from cattrs.converters import Converter
from cattrs.preconf.json import make_converter as make_json_converter, JsonConverter
from cattrs.preconf.pyyaml import make_converter as make_yaml_converter

unstruct_collection_overrides = {tuple: tuple}

T = TypeVar("T")

converters = {
    "json": make_json_converter(
        unstruct_collection_overrides=unstruct_collection_overrides
    ),
    "yaml": make_yaml_converter(
        unstruct_collection_overrides=unstruct_collection_overrides
    ),
    "unconfigured": Converter(
        unstruct_collection_overrides=unstruct_collection_overrides
    ),
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


# datetime serialization


def unstructure_datetime(obj: datetime) -> str:
    return obj.isoformat()


register_unstructure_hook(datetime, unstructure_datetime)


def structure_datetime(serialized: str, _) -> datetime:
    return datetime.fromisoformat(serialized)


register_structure_hook(datetime, structure_datetime)


def to_json(obj: Any, unstructure_as: Any = None) -> str:
    converter: JsonConverter = converters["json"]  # type: ignore
    return converter.dumps(obj, unstructure_as=unstructure_as, indent=2)


def from_json(serialized: str, cls: type[T]) -> T:
    converter: JsonConverter = converters["json"]  # type: ignore
    return converter.loads(serialized, cls)

def copy_converter() -> Converter:
    """Return a copy of a serialization converter with common hooks registered."""

    return converters["json"].copy()
