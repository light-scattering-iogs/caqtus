from __future__ import annotations

import enum
import functools
from collections.abc import Callable

from PySide6 import QtWidgets

from ._editor_builder import ValueEditor
from ...qtutil import QABCMeta


def generate_enum_editor[
    T: enum.Enum
](enum_type: type[T]) -> Callable[[], EnumEditor[T]]:
    """Generate an editor factory for an enum type.

    Returns:
        A factory function that creates an EnumEditor for the given enum type.
        The editor is a combobox with the name of each enum member as its items.
    """

    return functools.partial(EnumEditor[T], enum_type)


class EnumEditor[T: enum.Enum](QtWidgets.QComboBox, ValueEditor[T], metaclass=QABCMeta):
    def __init__(self, enum_type: type[T]):
        super().__init__(None)
        self._enum_type = enum_type
        self._index_to_value = {}
        self._value_to_index = {}
        for index, value in enumerate(enum_type):
            self.addItem(str(value.value))
            self._index_to_value[index] = value
            self._value_to_index[value] = index

    def set_value(self, value: T) -> None:
        try:
            index = self._value_to_index[value]
        except KeyError:
            raise ValueError(
                f"Value {value} is not a member of the enum {self._enum_type}"
            ) from None
        self.setCurrentIndex(index)

    def read_value(self) -> T:
        index = self.currentIndex()
        return self._index_to_value[index]

    def set_editable(self, editable: bool) -> None:
        self.setEnabled(editable)

    @property
    def widget(self) -> QtWidgets.QComboBox:
        return self
