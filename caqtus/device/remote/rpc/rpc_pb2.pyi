from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import (
    ClassVar as _ClassVar,
    Iterable as _Iterable,
    Mapping as _Mapping,
    Optional as _Optional,
    Union as _Union,
)

DESCRIPTOR: _descriptor.FileDescriptor

class ReturnValue(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SERIALIZED: _ClassVar[ReturnValue]
    PROXY: _ClassVar[ReturnValue]

SERIALIZED: ReturnValue
PROXY: ReturnValue

class CallRequest(_message.Message):
    __slots__ = ("function", "args", "kwargs", "return_value")

    class KwargsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bytes
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[bytes] = ...
        ) -> None: ...

    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    ARGS_FIELD_NUMBER: _ClassVar[int]
    KWARGS_FIELD_NUMBER: _ClassVar[int]
    RETURN_VALUE_FIELD_NUMBER: _ClassVar[int]
    function: bytes
    args: _containers.RepeatedScalarFieldContainer[bytes]
    kwargs: _containers.ScalarMap[str, bytes]
    return_value: ReturnValue
    def __init__(
        self,
        function: _Optional[bytes] = ...,
        args: _Optional[_Iterable[bytes]] = ...,
        kwargs: _Optional[_Mapping[str, bytes]] = ...,
        return_value: _Optional[_Union[ReturnValue, str]] = ...,
    ) -> None: ...

class CallResponse(_message.Message):
    __slots__ = ("success", "failure")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    FAILURE_FIELD_NUMBER: _ClassVar[int]
    success: bytes
    failure: bytes
    def __init__(
        self, success: _Optional[bytes] = ..., failure: _Optional[bytes] = ...
    ) -> None: ...
