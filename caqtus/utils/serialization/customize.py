from typing import TypeVar, Callable

from attrs import AttrsInstance
from cattrs.gen import (
    AttributeOverride,  # pyright: ignore[reportPrivateImportUsage]
    make_dict_unstructure_fn,
    make_dict_structure_fn,
)

from .converters import converters

_T = TypeVar("_T", bound=AttrsInstance)


def customize(**kwargs: AttributeOverride) -> Callable[[type[_T]], type[_T]]:
    def decorator(cls: type[_T]) -> type[_T]:
        for converter in converters.values():
            unstructure_hook = make_dict_unstructure_fn(
                cls, converter, **kwargs  # pyright: ignore[reportArgumentType]
            )
            converter.register_unstructure_hook(cls, unstructure_hook)

            structure_hook = make_dict_structure_fn(
                cls, converter, **kwargs  # pyright: ignore[reportArgumentType]
            )
            converter.register_structure_hook(cls, structure_hook)

        return cls

    return decorator
