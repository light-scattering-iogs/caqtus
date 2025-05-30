from cattrs.gen import override

from ._external_union import configure_external_union
from ._json import (
    JSON,
    JsonDict,
    JsonList,
    is_valid_json,
    is_valid_json_dict,
    is_valid_json_list,
)
from .converters import (
    converters,
    copy_converter,
    from_json,
    new_converter,
    register_structure_hook,
    register_unstructure_hook,
    structure,
    to_json,
    unstructure,
)
from .customize import customize
from .strategies import configure_tagged_union, include_subclasses, include_type

__all__ = [
    "converters",
    "structure",
    "unstructure",
    "register_structure_hook",
    "register_unstructure_hook",
    "to_json",
    "from_json",
    "customize",
    "override",
    "include_subclasses",
    "configure_tagged_union",
    "include_type",
    "JSON",
    "JsonDict",
    "JsonList",
    "is_valid_json",
    "is_valid_json_dict",
    "is_valid_json_list",
    "copy_converter",
    "configure_external_union",
    "new_converter",
]
