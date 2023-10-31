from typing import Any

from cattrs.converters import Converter
from cattrs.preconf.json import make_converter as make_json_converter
from cattrs.preconf.pyyaml import make_converter as make_yaml_converter

unstruct_collection_overrides = {tuple: tuple}

converters = {
    "json": make_json_converter(unstruct_collection_overrides=unstruct_collection_overrides),
    "yaml": make_yaml_converter(unstruct_collection_overrides=unstruct_collection_overrides),
    "unconfigured": Converter(unstruct_collection_overrides=unstruct_collection_overrides)
}


def unstructure(obj: Any, unstructure_as: Any = None):
    return converters["unconfigured"].unstructure(obj, unstructure_as=unstructure_as)

def structure(obj: Any, cls: Any = None):
    return converters["unconfigured"].structure(obj, cls)
