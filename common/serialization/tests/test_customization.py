from attrs import define

import serialization


def test() -> None:
    @serialization.customize(_b=serialization.override(omit=True))
    @define
    class Test:
        a: int = 1
        _b: float = 2.0

    assert serialization.unstructure(Test()) == {"a": 1}
