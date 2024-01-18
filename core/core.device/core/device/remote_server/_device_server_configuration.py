from pydantic import SecretStr

from util import attrs, serialization


def secret_str_converter(value: str | SecretStr) -> SecretStr:
    if isinstance(value, SecretStr):
        return value
    elif isinstance(value, str):
        return SecretStr(value)
    else:
        raise TypeError(f"Expected str or SecretStr, got {value} of type {type(value)}")


@attrs.define
class DeviceServerConfiguration:
    address: str = attrs.field(converter=str, on_setattr=attrs.setters.convert)
    port: int = attrs.field(converter=int, on_setattr=attrs.setters.convert)
    authkey: SecretStr = attrs.field(
        converter=secret_str_converter, on_setattr=attrs.setters.convert
    )


def secret_str_unstructure(secret_str: SecretStr) -> str:
    return secret_str.get_secret_value()


serialization.register_unstructure_hook(SecretStr, secret_str_unstructure)


def secret_str_structure(secret_str, _) -> SecretStr:
    return SecretStr(secret_str)


serialization.register_structure_hook(SecretStr, secret_str_structure)
