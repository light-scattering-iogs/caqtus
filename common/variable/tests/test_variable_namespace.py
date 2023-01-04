import pytest

from variable.variable_namespace import split_names


def test_split_namespaces_variable_name():
    assert split_names("namespace1.namespace2.variable_name") == (
        "namespace1",
        "namespace2",
        "variable_name",
    )
    assert split_names("variable_name") == ("variable_name",)
    with pytest.raises(ValueError):
        assert split_names("variable_name&") == ("variable_name&",)
