import attrs


@attrs.define
class InsecureRPCConfiguration:
    host: str = attrs.field(converter=str, on_setattr=attrs.setters.convert)
    port: int = attrs.field(converter=int, on_setattr=attrs.setters.convert)


RPCConfiguration = InsecureRPCConfiguration
