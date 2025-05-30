from collections.abc import Callable
from typing import Any

import cattrs


def default_tag_generator(typ: type) -> str:
    """Return the class name."""
    return typ.__name__


def configure_external_union(
    union: Any,
    converter: cattrs.BaseConverter,
    tag_generator: Callable[[type], str] = default_tag_generator,
) -> None:
    args = union.__args__
    cls_to_tag = {cl: tag_generator(cl) for cl in args}
    cls_to_unstructure_hook = {cl: converter.get_unstructure_hook(cl) for cl in args}
    tag_to_structure_hook = {
        cls_to_tag[cl]: converter.get_structure_hook(cl) for cl in args
    }

    for cl in args:
        tag = tag_generator(cl)
        unstructure_hook = converter.get_unstructure_hook(cl)
        structure_hook = converter.get_structure_hook(cl)
        cls_to_tag[cl] = tag
        cls_to_unstructure_hook[cl] = unstructure_hook
        tag_to_structure_hook[tag] = structure_hook

    def unstructure_external_union(
        val,
    ) -> dict:
        cls = val.__class__
        res = cls_to_unstructure_hook[cls](val)
        return {cls_to_tag[cls]: res}

    def structure_external_union(val: dict, _):
        if len(val) != 1:
            raise ValueError("Expected a single key in the dictionary for union type.")
        tag = next(iter(val))
        try:
            structure_hook = tag_to_structure_hook[tag]
        except KeyError:
            raise ValueError(f"Unknown tag '{tag}' for union type.") from None
        return structure_hook(val[tag], _)

    converter.register_unstructure_hook(union, unstructure_external_union)
    converter.register_structure_hook(union, structure_external_union)