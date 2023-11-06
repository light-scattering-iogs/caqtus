from ast import literal_eval
from collections.abc import Hashable
from typing import Protocol, runtime_checkable

from util import serialization


@runtime_checkable
class AtomLabel(Hashable, Protocol):
    """A label that can be used to refer to an atom.

    It must be possible to use the label as a key in a dictionary, so it must be
    hashable and immutable.
    Typically, we want to represent the position of an atom along a chain or in a
    lattice, so for example AtomLabel can be an integer or a tuple of integers, which
    have by default the required properties.
    """

    def __str__(self) -> str:
        ...

    def __repr__(self) -> str:
        ...

    def __eq__(self, other) -> bool:
        ...


def unstructure_atom_label(label: AtomLabel) -> str:
    # We cannot serialize the label as is, because tuple[int, int] is a valid label,
    # but it is not possible to use it as a key in a dictionary in json.
    # So we serialize the label using repr, which is a string that can be used to
    # reconstruct the label.
    return repr(label)


def structure_atom_label(serialized: str, _) -> AtomLabel:
    # We use literal_eval to reconstruct the label.
    # This restricts the possible types of labels to those that can be represented as
    # literals in python.
    label = literal_eval(serialized)
    if not isinstance(label, AtomLabel):
        raise TypeError(f"Expected AtomLabel, got {type(label)}")
    return label


serialization.register_unstructure_hook(AtomLabel, unstructure_atom_label)
serialization.register_structure_hook(AtomLabel, structure_atom_label)
