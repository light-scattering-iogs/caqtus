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
        if isinstance(value, str):
            if format_spec == "device":
                value = f"device '{value}'"
                format_spec = ""
            elif format_spec == "device server":
                value = f"device server '{value}'"
                format_spec = ""
        return super().format(value, format_spec)


caqtus_formatter = CaqtusFormatter()


def fmt(s: str, *args, **kwargs):
    return caqtus_formatter.format(s, *args, **kwargs)
