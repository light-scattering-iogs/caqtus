from sequence.runtime import SequencePath


def test_sequence_path():
    assert SequencePath.is_valid_path("a/b/c")
    assert not SequencePath.is_valid_path("a/b/c/")
    assert not SequencePath.is_valid_path("/a/b/c")
