from core.session import SequencePath


def test():
    path = SequencePath("a.b.c")
    print(path.get_ancestors())
    assert path.get_ancestors() == [
        SequencePath.root(),
        SequencePath("a"),
        SequencePath("a.b"),
    ]
