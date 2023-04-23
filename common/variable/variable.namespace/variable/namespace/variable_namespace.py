import copy
import re
from collections.abc import MutableMapping, Mapping
from types import SimpleNamespace
from typing import Any

from variable.name import VariableName, DottedVariableName


class VariableNamespace(MutableMapping):
    """A dict like object that can contain variables or other namespaces."""

    def __init__(self, initial_variables: Mapping[DottedVariableName, Any] = None):
        if initial_variables is None:
            initial_variables = dict()
        self._dict: dict[VariableName, Any | SimpleNamespace] = dict()
        for key, value in initial_variables.items():
            self[key] = value

    def __getitem__(self, key: DottedVariableName) -> Any:
        return self._getitem(key, create=False)

    def _getitem(self, key: DottedVariableName, create=False):
        """Get an item from the dict.

        Parameters:
            key: The key to get.
            create: If the key does not exist and this is True, create a new namespace at the key. If the key does not
            exist and this is False, raise a KeyError.

        Returns:
            The value at the key.
        """

        match key.individual_names:
            case (variable,):
                try:
                    return self._dict[variable]
                except KeyError as error:
                    if create:
                        self._dict[variable] = SimpleNamespace()
                        return self._dict[variable]
                    else:
                        raise error
            case (*namespaces, variable):
                parent_name = DottedVariableName.from_individual_names(namespaces)
                try:
                    parent = self._getitem(
                        parent_name,
                        create=create,
                    )
                except AttributeError as error:
                    if create:
                        parent = self[parent_name] = SimpleNamespace()
                    else:
                        raise error
                variable = str(variable)
                if not hasattr(parent, variable) and create:
                    setattr(parent, variable, SimpleNamespace())
                return getattr(parent, variable)

    def __setitem__(self, key: DottedVariableName, value: Any) -> None:
        match key.individual_names:
            case (variable,):
                self._dict[variable] = value
            case (*namespaces, variable):
                setattr(
                    self._getitem(
                        DottedVariableName.from_individual_names(namespaces),
                        create=True,
                    ),
                    str(variable),
                    value,
                )

    def __delitem__(self, key: str):
        raise NotImplementedError("Deleting items is not supported.")

    def __len__(self):
        return len(self._dict)

    def __iter__(self):
        return iter(self._dict)

    def __repr__(self):
        kwargs = ", ".join(f"{key}={value}" for key, value in self.items())
        return f"{self.__class__.__name__}({kwargs})"

    def __or__(self, other):
        if isinstance(other, Mapping):
            new = copy.deepcopy(self)
            new.update(other)
            return new
        else:
            raise TypeError


NAME_REGEX = re.compile(r"^[^\W\d]\w*$")


def split_names(string: str) -> tuple[str, ...]:
    """Split a dotted variable name into individual names.

    Parameters:
        string: The expression to split. ex: "namespace1.namespace2.variable_name"

    Returns:
        The individual names. ex: ("namespace1", "namespace2", "variable_name")

    Raises:
        ValueError if any of the names are invalid.
    """

    names = tuple(string.split("."))
    for name in names:
        if not NAME_REGEX.match(name):
            raise ValueError(f"Invalid name: '{name}' in '{string}'")

    return names


def join_names(names: tuple[str, ...]) -> str:
    """Join a tuple of names into a single string.

    Parameters:
        names: The names to join. ex: ("namespace1", "namespace2", "variable_name")

    Returns
        The joined names. ex: "namespace1.namespace2.variable_name"
    """

    return ".".join(names)
