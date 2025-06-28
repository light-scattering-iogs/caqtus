import abc
from collections.abc import Callable, Set
from typing import Generic, TypeAlias, TypeVar

import caqtus.gui.qtutil.qabc as qabc
from caqtus.types.iteration import IterationConfiguration
from caqtus.types.variable_name import DottedVariableName

T = TypeVar("T", bound=IterationConfiguration)


class SequenceIterationEditor(Generic[T], metaclass=qabc.QABCMeta):
    @abc.abstractmethod
    def get_iteration(self) -> T:
        raise NotImplementedError

    @abc.abstractmethod
    def set_iteration(self, iteration: T):
        raise NotImplementedError

    @abc.abstractmethod
    def set_read_only(self, read_only: bool):
        """Sets the editor in read-only mode.

        When the editor is in read-only mode, the user cannot edit the steps.

        Even if the editor is in read-only mode, the iteration can still be set
        programmatically with :meth:`set_iteration`.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def is_read_only(self) -> bool:
        """Returns whether the editor is in read-only mode."""

        raise NotImplementedError

    @abc.abstractmethod
    def set_available_parameter_names(self, parameter_names: Set[DottedVariableName]):
        """Set the names of the parameters that are defined externally."""

        raise NotImplementedError


IterationEditorCreator: TypeAlias = Callable[[T], SequenceIterationEditor[T]]
