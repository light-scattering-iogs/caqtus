from typing import Optional

from PyQt6.QtCore import Qt, QModelIndex
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QTreeView, QWidget, QAbstractItemView, QMenu

from experiment.configuration import ExperimentConfig
from expression import Expression
from sequence.configuration import Step, VariableDeclaration, ExecuteShot
from ..config_settings_editor import ConfigSettingsEditor
from ...steps_editor import StepDelegate, StepsModel


class SequenceHeaderEditor(QTreeView, ConfigSettingsEditor):
    """Editor for the steps that are executed before each sequence

    Only allows to declare constants at the moment.
    """

    def get_experiment_config(self) -> ExperimentConfig:
        return self.model.get_config()

    def __init__(
        self,
        config: ExperimentConfig,
        tree_label: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(config, tree_label, parent)

        self.model = SequenceHeaderModel(config)
        self.setModel(self.model)
        delegate = StepDelegate()
        self.setItemDelegate(delegate)
        self.setHeaderHidden(True)
        self.setAnimated(True)
        self.setContentsMargins(0, 0, 0, 0)

        # noinspection PyUnresolvedReferences
        self.model.modelReset.connect(lambda: self.expandAll())
        self.expandAll()
        self.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragDropOverwriteMode(False)
        # noinspection PyUnresolvedReferences
        self.model.rowsInserted.connect(lambda _: self.expandAll())

        self.setItemsExpandable(False)

        # noinspection PyUnresolvedReferences
        self.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, position):
        index = self.indexAt(position)
        # noinspection PyTypeChecker

        menu = QMenu(self)

        add_menu = QMenu()
        add_menu.setTitle("Add...")
        menu.addMenu(add_menu)

        create_variable_action = QAction("constant")
        add_menu.addAction(create_variable_action)
        # noinspection PyUnresolvedReferences
        create_variable_action.triggered.connect(
            lambda: self.model.insert_step(
                VariableDeclaration(name="", expression=Expression(body="...")), index
            )
        )
        menu.exec(self.mapToGlobal(position))


class SequenceHeaderModel(StepsModel):
    def __init__(self, config: ExperimentConfig):
        super().__init__()
        self._config = config

    def get_config(self) -> ExperimentConfig:
        return self._config

    @property
    def root(self) -> Step:
        return self._config.header

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if index.isValid() and index.column() == 0:
            flags = super().flags(index)
            flags |= Qt.ItemFlag.ItemIsEditable
            if not isinstance(
                self.data(index, Qt.ItemDataRole.DisplayRole),
                (VariableDeclaration, ExecuteShot),
            ):
                flags |= Qt.ItemFlag.ItemIsDropEnabled
        else:
            flags = Qt.ItemFlag.NoItemFlags
        return flags

    def supportedDragActions(self) -> Qt.DropAction:
        return Qt.DropAction.MoveAction
