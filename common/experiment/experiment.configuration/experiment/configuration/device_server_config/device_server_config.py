from pydantic import SecretStr

from settings_model import YAMLSerializable
from util import attrs, serialization


@attrs.define
class DeviceServerConfiguration:
    address: str = attrs.field(converter=str, on_setattr=attrs.setters.convert)
    port: int = attrs.field(converter=int, on_setattr=attrs.setters.convert)
    authkey: SecretStr = attrs.field(
        converter=SecretStr, on_setattr=attrs.setters.convert
    )


YAMLSerializable.register_attrs_class(DeviceServerConfiguration)


def secret_str_unstructure(secret_str: SecretStr) -> str:
    return secret_str.get_secret_value()


serialization.register_unstructure_hook(SecretStr, secret_str_unstructure)


def secret_str_structure(secret_str) -> SecretStr:
    return SecretStr(secret_str)


serialization.register_structure_hook(SecretStr, secret_str_structure)
