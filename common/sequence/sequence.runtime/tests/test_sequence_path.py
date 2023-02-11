from sequence.runtime import SequencePath


def test_sequence_path():
    assert SequencePath.is_valid_path("a/b/c")
    assert not SequencePath.is_valid_path("a/b/c/")
    assert not SequencePath.is_valid_path("/a/b/c")


def test_ancestors():
    assert SequencePath("a/b/c").get_ancestors() == ["a", "a/b"]
    assert SequencePath("a/b/c/d").get_ancestors() == ["a", "a/b", "a/b/c"]
    assert SequencePath("a").get_ancestors() == []

    assert SequencePath("a/b/c").get_ancestors(strict=False) == ["a", "a/b", "a/b/c"]
