from pydantic import SecretStr

from settings_model import YAMLSerializable
from util import attrs


@attrs.define
class DeviceServerConfiguration:
    address: str = attrs.field(converter=str, on_setattr=attrs.setters.convert)
    port: int = attrs.field(converter=int, on_setattr=attrs.setters.convert)
    authkey: SecretStr = attrs.field(
        converter=SecretStr, on_setattr=attrs.setters.convert
    )


YAMLSerializable.register_attrs_class(DeviceServerConfiguration)
