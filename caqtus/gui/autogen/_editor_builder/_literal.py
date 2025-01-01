from __future__ import annotations

import functools
from collections.abc import Iterable

from PySide6 import QtWidgets

from ._editor_builder import EditorFactory, ValueEditor


def build_literal_editor(*values) -> EditorFactory[LiteralEditor]:
    """Build an editor for a predefined set of values.

    The editor will be a combo box proposing the given values.

    Args:
        values: The values to propose in the combo box.
            They must be hashable and convertible to string.
    """

    if not values:
        raise ValueError("At least one value must be provided")
    return functools.partial(LiteralEditor, values)


class LiteralEditor(ValueEditor):
    def __init__(self, values: Iterable) -> None:
        if not values:
            raise ValueError("At least one value must be provided")
        self.combo_box = QtWidgets.QComboBox()
        self.value_to_index = {}
        self.index_to_value = {}
        for index, value in enumerate(values):
            self.combo_box.addItem(str(value))
            self.value_to_index[value] = index
            self.index_to_value[index] = value
        self.combo_box.setCurrentIndex(0)

    def set_value(self, value) -> None:
        index = self.value_to_index[value]
        self.combo_box.setCurrentIndex(index)

    def read_value(self):
        return self.index_to_value[self.combo_box.currentIndex()]

    def set_editable(self, editable: bool) -> None:
        self.combo_box.setEnabled(editable)

    def widget(self) -> QtWidgets.QComboBox:
        return self.combo_box
