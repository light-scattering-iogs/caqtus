import string
from typing import TYPE_CHECKING

from caqtus.types.units.units import UnitLike

if TYPE_CHECKING:
    from caqtus.types.expression import Expression
    from caqtus.types.variable_name import DottedVariableName


class CaqtusFormatter(string.Formatter):
    """Custom formatter for caqtus.

    Instances of this class can be used to format strings with the following format
    specifiers:
    - :device: to format a string as a device name
    - :device server: to format a string as a remote server name

    It is useful to use this formatter to display objects in the caqtus package
    consistently.
    This allows parsing the string produced by the formatter to find the fields.

    Allowed format specifiers:

    * :step: to format a :data:`tuple[int, str]` as a step index and name.
    * :device: to format a :class:`str` as the name of a device.
    * :device server: to format a :class:`str` as the name of a remote server.
    * :expression: to format a :class:`caqtus.types.expressions.Expression` as the
    value of an expression.
    * :parameter assignment: to format a
    :data:`tuple[str, caqtus.types.expressions.Expression]` as the name and value of a
    parameter assignment.
    * :device parameter: to format a :data:`typle[str, Any]` as the name and value of
    a parameter for a device.

    Example:
    ```
    formatter = CaqtusFormatter()
    print(formatter.format("{:device}", "name"))

    # Output: device: 'name'
    ```
    """

    def format_field(self, value, format_spec):
        if format_spec == "step":
            step_index, step_name = value
            if not isinstance(step_index, int):
                raise ValueError("Step index must be an integer")
            if not isinstance(step_name, str):
                raise ValueError("Step name must be a string")
            value = f"step {step_index} ({step_name})"
        elif format_spec == "device":
            value = f"device '{value}'"
        elif format_spec == "device server":
            value = f"device server '{value}'"
        elif format_spec == "expression":
            value = f"expression '{value}'"
        elif format_spec == "parameter assignment":
            parameter_name, parameter_value = value
            value = f"parameter assignment '{parameter_name}' = '{parameter_value}'"
        elif format_spec == "type":
            value = f"type '{value.__name__}'"
        elif format_spec == "shot":
            if not isinstance(value, int):
                raise ValueError("Shot number must be an integer")
            value = f"shot {value}"
        elif format_spec == "device parameter":
            parameter_name, parameter_value = value
            value = f"device parameter '{parameter_name}' = '{parameter_value}'"
        return super().format(value, "")


caqtus_formatter = CaqtusFormatter()


def fmt_param_assign(name: "DottedVariableName", expression: "Expression") -> str:
    return f"parameter assignment '{name}' = '{expression}'"


def fmt_type(value: type | str) -> str:
    return f"type '{value.__name__}'"


def device_param(name: str, value: str) -> str:
    return f"device parameter '{name}' = '{value}'"


def expression(expression: "Expression") -> str:
    return f"expression '{expression}'"


def unit(value: UnitLike) -> str:
    return f"unit '{value}'"


def type_(value: type | str) -> str:
    if isinstance(value, type):
        return f"type '{value.__name__}'"
    elif isinstance(value, str):
        return f"type '{value}'"
    else:
        raise ValueError("Invalid type value")


def fmt(s: str, *args, **kwargs):
    return caqtus_formatter.format(s, *args, **kwargs)
