from abc import ABCMeta, abstractmethod
from typing import Optional

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QWidget

from experiment_config import ExperimentConfig


class QABCMeta(type(QObject), ABCMeta):
    pass


class ConfigSettingsEditor(QWidget, metaclass=QABCMeta):
    """An abstract interface defining how a widget should edit a group of settings

    Every time a settings group is selected in the config editor, a widget is created to edit that group.
    """

    def __init__(
        self,
        config: ExperimentConfig,
        tree_label: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

    @abstractmethod
    def get_experiment_config(self) -> ExperimentConfig:
        ...
