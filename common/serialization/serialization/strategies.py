from attr import AttrsInstance
from cattrs.strategies import include_subclasses as _include_subclasses

from .converters import converters


def include_subclasses(parent_class: type[AttrsInstance]) -> None:
    for converter in converters.values():
        _include_subclasses(parent_class, converter)
