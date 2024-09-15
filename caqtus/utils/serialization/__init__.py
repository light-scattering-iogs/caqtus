from cattrs.gen import override

from .converters import (
    unstructure,
    converters,
    structure,
    register_unstructure_hook,
    register_structure_hook,
    to_json,
    from_json,
    copy_converter,
)
from .customize import customize
from .json import JSON, is_valid_json, is_valid_json_dict, is_valid_json_list
from .strategies import include_subclasses, include_type, configure_tagged_union

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
    "is_valid_json",
    "is_valid_json_dict",
    "is_valid_json_list",
    "copy_converter",
]
