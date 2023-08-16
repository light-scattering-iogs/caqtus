from typing import Any

from cattrs.converters import Converter
from cattrs.preconf.json import make_converter as make_json_converter
from cattrs.preconf.pyyaml import make_converter as make_yaml_converter

converters = {
    "json": make_json_converter(),
    "yaml": make_yaml_converter(),
    "unconfigured": Converter(),
}


def unstructure(obj: Any, unstructure_as: Any = None):
    return converters["unconfigured"].unstructure(obj, unstructure_as=unstructure_as)
