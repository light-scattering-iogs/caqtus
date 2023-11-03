from functools import partial
from typing import Optional, Callable, Any, TypeVar

from attr import AttrsInstance
from cattrs import BaseConverter
from cattrs.strategies import (
    include_subclasses as _include_subclasses,
    configure_tagged_union,
)

from .converters import converters

_C = TypeVar("_C", bound=AttrsInstance)


def include_type(tag_name: str = "class") -> Callable[[Any, BaseConverter], Any]:
    return partial(configure_tagged_union, tag_name=tag_name)


def include_subclasses(
    parent_class: type[_C],
    subclasses: Optional[tuple[type[_C]]] = None,
    union_strategy: Optional[Callable[[Any, BaseConverter], Any]] = None,
) -> None:
    for converter in converters.values():
        _include_subclasses(
            parent_class,
            converter,
            subclasses=subclasses,
            union_strategy=union_strategy,
        )
