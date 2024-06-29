import attrs


@attrs.define
class InsecureRPCConfiguration:
    target: str = attrs.field(converter=str, on_setattr=attrs.setters.convert)


RPCConfiguration = InsecureRPCConfiguration
