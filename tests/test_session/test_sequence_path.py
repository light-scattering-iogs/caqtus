from hypothesis import given

from caqtus.session import PureSequencePath
from .generate_path import path, path_name


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


def test_is_descendant():
    ancestor = PureSequencePath.root() / "ancestor"
    descendant = ancestor / "descendant"

    assert descendant.is_descendant_of(ancestor)


def test_is_not_descendant():
    ancestor = PureSequencePath.root() / "ancestor"
    descendant = ancestor / "descendant"
    other = PureSequencePath.root() / "other"

    assert not descendant.is_descendant_of(other)


def test_is_not_descendant_of_itself():
    path = PureSequencePath.root() / "path"

    assert not path.is_descendant_of(path)
