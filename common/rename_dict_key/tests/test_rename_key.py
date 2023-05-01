import pytest

from rename_dict_key import rename_dict_key


def test_rename_dict_key():
    # Test renaming a key that exists in the dictionary
    d = {"a": 1, "b": 2, "c": 3}
    new_d = rename_dict_key(d, "b", "x")
    assert new_d == {"a": 1, "x": 2, "c": 3}

    # Test renaming a key that doesn't exist in the dictionary
    d = {"a": 1, "b": 2, "c": 3}
    new_d = rename_dict_key(d, "d", "x")
    assert new_d == {"a": 1, "b": 2, "c": 3}

    # Test renaming a key to a new name that already exists in the dictionary
    d = {"a": 1, "b": 2, "c": 3}
    with pytest.raises(ValueError):
        rename_dict_key(d, "b", "a")

    # Test renaming an empty dictionary
    d = {}
    new_d = rename_dict_key(d, "a", "b")
    assert new_d == {}

    # Test that the order is preserved
    d = {"a": 1, "b": 2, "c": 3}
    new_d = rename_dict_key(d, "b", "x")
    assert list(new_d.keys()) == ["a", "x", "c"]

    # Test that the original dictionary is not modified
    d = {"a": 1, "b": 2, "c": 3}
    rename_dict_key(d, "b", "x")
    assert d == {"a": 1, "b": 2, "c": 3}
