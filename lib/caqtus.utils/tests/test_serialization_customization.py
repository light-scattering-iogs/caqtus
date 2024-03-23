from caqtus.utils import attrs, serialization


def test() -> None:
    @serialization.customize(_b=serialization.override(omit=True))
    @attrs.define
    class Test:
        a: int = 1
        _b: float = 2.0

    assert serialization.unstructure(Test()) == {"a": 1}
