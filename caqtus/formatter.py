import string


class CaqtusFormatter(string.Formatter):
    """Custom formatter for caqtus.

    Instances of this class can be used to format strings with the following format
    specifiers:
    - :device: to format a string as a device name
    - :device server: to format a string as a remote server name

    It is useful to use this formatter to display objects in the caqtus package
    consistently.
    This allows parsing the string produced by the formatter to find the fields.

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
        elif format_spec == "parameter":
            value = f"parameter '{value}'"
        elif format_spec == "type":
            value = f"type '{value.__name__}'"
        elif format_spec == "shot":
            if not isinstance(value, int):
                raise ValueError("Shot number must be an integer")
            value = f"shot {value}"

        return super().format(value, "")


caqtus_formatter = CaqtusFormatter()


def fmt(s: str, *args, **kwargs):
    return caqtus_formatter.format(s, *args, **kwargs)
