from hypothesis import given
from .generate_path import path, path_name
from caqtus.session.path import PureSequencePath


@given(path_name)
def test_name(name):
    assert PureSequencePath.is_valid_name(name)


@given(path)
def test_path(p):
    assert PureSequencePath(str(p)) == p

    if not p.is_root():
        assert p.parent / p.name == p


def test_whitespace_names():
    assert not PureSequencePath.is_valid_name(" ")
    assert not PureSequencePath.is_valid_name("")
    assert not PureSequencePath.is_valid_name(" a")
    assert PureSequencePath.is_valid_name("a ")


def test_special_characters():
    assert PureSequencePath.is_valid_name(".")
