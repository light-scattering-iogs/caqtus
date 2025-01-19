# pyright: strict
from __future__ import annotations

from typing import assert_never

import attrs
from PySide6 import QtWidgets

type WidgetState = NoSequenceSet
"""Describes the state of a SequenceDevicesEditor widget."""

type _WidgetState = _NoSequenceSet


@attrs.frozen
class NoSequenceSet:
    """The widget is in a state where no sequence has been set."""

    pass


@attrs.frozen
class _NoSequenceSet(NoSequenceSet):
    pass


class SequenceDevicesEditor(QtWidgets.QWidget):
    """A widget for displaying and editing the device configurations of a sequence."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)

        self._layout = QtWidgets.QVBoxLayout()
        self._tab_widget = QtWidgets.QTabWidget()
        clear_and_disable_tab_widget(self._tab_widget)

        self._setup_ui()

        self._state: _WidgetState = _NoSequenceSet()

    def _setup_ui(self) -> None:
        self.setLayout(self._layout)
        self._layout.addWidget(self._tab_widget)

    def transition(self, state: WidgetState) -> None:
        """Changes the state of the widget to the given state.

        Changes the state of the widget to the given state.
        """

        new_state = None

        match state:
            case NoSequenceSet():
                clear_and_disable_tab_widget(self._tab_widget)
                new_state = _NoSequenceSet()
            case _:
                assert_never(state)

        self._state = new_state

    @property
    def state(self) -> WidgetState:
        """The current state of the widget.

        Returns:
            A reference to the current state of the widget.
            The value returned becomes invalid whenever a method changing the widget's
            state is called.
        """

        return self._state


def delete_all_tabs(tab_widget: QtWidgets.QTabWidget) -> None:
    """Removes all tabs from the tab widget and deletes the widgets they contain."""

    while tab_widget.count() > 0:
        tab_widget.widget(0).deleteLater()
        tab_widget.removeTab(0)


def clear_and_disable_tab_widget(tab_widget: QtWidgets.QTabWidget) -> None:
    tab_widget.setEnabled(False)
    delete_all_tabs(tab_widget)
