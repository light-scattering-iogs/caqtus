from caqtus.utils import serialization

from ..variable_name import configure_variable_name_conversion_hooks
from ._steps import ExecuteShot
from ._tunable_parameter_config import (
    configure_tunable_parameter_conversion_hooks,
)

_converter = serialization.new_converter()
configure_tunable_parameter_conversion_hooks(_converter)
configure_variable_name_conversion_hooks(_converter)


@_converter.register_unstructure_hook
def unstructure_hook(execute_shot: ExecuteShot):
    return {"execute": "shot"}


@_converter.register_structure_hook
def structure_hook(data: str, _) -> ExecuteShot:
    return ExecuteShot()
