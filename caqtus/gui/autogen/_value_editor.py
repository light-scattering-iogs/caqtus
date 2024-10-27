import abc
from typing import Optional

from PySide6.QtWidgets import QWidget


class ValueEditor[T](abc.ABC):
    """Allows to edit a value of type T.

    Args:
        value: The initial value to edit.
            Once initialized, the value can only be changed by the user through the
            widget.
        parent: The parent widget of the editor.
    """

    @abc.abstractmethod
    def __init__(self, value: T, parent: Optional[QWidget] = None) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def read_value(self) -> T:
        """Return the current value displayed in the editor."""

        raise NotImplementedError

    @abc.abstractmethod
    def set_editable(self, editable: bool) -> None:
        """Set whether the editor is editable or not.

        When initialized, the editor is editable.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def widget(self) -> QWidget:
        """Return the widget that allows to edit the value."""

        raise NotImplementedError
