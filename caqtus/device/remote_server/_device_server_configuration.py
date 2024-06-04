from typing import TypeAlias

import attrs
import grpc
from pydantic import SecretStr

from caqtus.utils import serialization


def secret_str_converter(value: str | SecretStr) -> SecretStr:
    if isinstance(value, SecretStr):
        return value
    elif isinstance(value, str):
        return SecretStr(value)
    else:
        raise TypeError(f"Expected str or SecretStr, got {value} of type {type(value)}")


@attrs.define
class LocalServerCredentials:
    connection_type: grpc.LocalConnectionType

    def get_credentials(self) -> grpc.ChannelCredentials:
        return grpc.local_channel_credentials(self.connection_type)


Credentials: TypeAlias = LocalServerCredentials


@attrs.define
class DeviceServerConfiguration:
    target: str = attrs.field(converter=str, on_setattr=attrs.setters.convert)
    credentials: Credentials = attrs.field()


def secret_str_unstructure(secret_str: SecretStr) -> str:
    return secret_str.get_secret_value()


serialization.register_unstructure_hook(SecretStr, secret_str_unstructure)


def secret_str_structure(secret_str, _) -> SecretStr:
    return SecretStr(secret_str)


serialization.register_structure_hook(SecretStr, secret_str_structure)
