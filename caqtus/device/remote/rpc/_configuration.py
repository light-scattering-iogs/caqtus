from typing import TypeAlias

import attrs
import grpc


@attrs.define
class LocalRPCCredentials:
    connection_type: grpc.LocalConnectionType

    def get_channel_credentials(self) -> grpc.ChannelCredentials:
        return grpc.local_channel_credentials(self.connection_type)

    def get_server_credentials(self) -> grpc.ServerCredentials:
        return grpc.local_server_credentials(self.connection_type)


Credentials: TypeAlias = LocalRPCCredentials


@attrs.define
class SecureRPCConfiguration:
    target: str = attrs.field(converter=str, on_setattr=attrs.setters.convert)
    credentials: Credentials = attrs.field()


@attrs.define
class InsecureRPCConfiguration:
    host: str = attrs.field(converter=str, on_setattr=attrs.setters.convert)
    port: int = attrs.field(converter=int, on_setattr=attrs.setters.convert)


RPCConfiguration = SecureRPCConfiguration | InsecureRPCConfiguration
