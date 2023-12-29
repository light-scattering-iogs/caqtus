import hypothesis.strategies
from hypothesis import given

from core.session.path import PureSequencePath, _PATH_NAME_REGEX

path_name = hypothesis.strategies.from_regex(_PATH_NAME_REGEX)
path_parts = hypothesis.strategies.lists(path_name, min_size=0)
path = hypothesis.strategies.builds(PureSequencePath.from_parts, path_parts)


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
