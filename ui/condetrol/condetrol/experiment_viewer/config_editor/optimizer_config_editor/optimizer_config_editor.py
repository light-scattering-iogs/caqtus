from typing import Optional

from PyQt6.QtCore import QAbstractListModel, QModelIndex, Qt
from PyQt6.QtWidgets import QWidget

from experiment.configuration import ExperimentConfig, OptimizerConfiguration
from yaml_clipboard_mixin import YAMLClipboardMixin
from .optimizer_config_editor_ui import Ui_OptimizerConfigEditor
from .optimizer_editor_ui import Ui_OptimizerEditor
from ..config_settings_editor import ConfigSettingsEditor


class OptimizerConfigEditor(
    ConfigSettingsEditor, YAMLClipboardMixin, Ui_OptimizerConfigEditor
):
    def __init__(
        self,
        experiment_config: ExperimentConfig,
        tree_label: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(experiment_config, tree_label, parent)

        self.setupUi(self)
        self.list_view.doubleClicked.connect(self.on_list_view_clicked)
        self.current_optimizer: Optional[OptimizerWidget] = None

        self.update_ui(self._experiment_config.optimization_configurations)

    def update_ui(self, optimization_configurations: dict[str, OptimizerConfiguration]):
        model = OptimizersModel(optimization_configurations)
        self.list_view.setModel(model)
        if self.current_optimizer:
            self.current_optimizer.deleteLater()
            self.current_optimizer = None

    def on_list_view_clicked(self, index: QModelIndex):
        if not index.isValid():
            return

        self.read_current_optimizer()
        if self.current_optimizer:
            self.current_optimizer.deleteLater()
            self.current_optimizer = None

        optimizer_name = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        self.current_optimizer = OptimizerWidget(
            optimizer_name,
            self._experiment_config.optimization_configurations[optimizer_name],
        )
        self.layout().addWidget(self.current_optimizer, 1)

    def read_current_optimizer(self):
        if self.current_optimizer:
            optimizer_config = self.current_optimizer.get_optimizer_configuration()
            self._experiment_config.optimization_configurations[
                self.current_optimizer.name
            ] = optimizer_config

    def get_experiment_config(self) -> ExperimentConfig:
        self.read_current_optimizer()
        return super().get_experiment_config()

    def convert_to_external_use(self):
        self.read_current_optimizer()
        return self._experiment_config.optimization_configurations

    def update_from_external_source(self, optimization_configurations):
        self._experiment_config.optimization_configurations = (
            optimization_configurations
        )
        self.update_ui(optimization_configurations)


class OptimizerWidget(QWidget, Ui_OptimizerEditor):
    def __init__(self, name: str, optimizer_configuration: OptimizerConfiguration):
        super().__init__()
        self.name = name
        self.setupUi(self)

        self.update_ui(optimizer_configuration)

    def update_ui(self, optimizer_configuration: OptimizerConfiguration):
        self.description_text_edit.setText(optimizer_configuration.description)
        self.script_path_line_edit.setText(str(optimizer_configuration.script_path))
        self.parameters_line_edit.setText(optimizer_configuration.parameters)
        self.working_directory_line_edit.setText(
            str(optimizer_configuration.working_directory)
        )

    def get_optimizer_configuration(self) -> OptimizerConfiguration:
        return OptimizerConfiguration(
            description=self.description_text_edit.toPlainText(),
            script_path=self.script_path_line_edit.text(),
            parameters=self.parameters_line_edit.text(),
            working_directory=self.working_directory_line_edit.text(),
        )


class OptimizersModel(QAbstractListModel):
    def __init__(self, optimizer_configurations: dict[str, OptimizerConfiguration]):
        super().__init__()
        self._optimizer_configurations = optimizer_configurations

    def rowCount(self, parent: QModelIndex = ...) -> int:
        if not parent.isValid():
            return len(self._optimizer_configurations)
        else:
            return 0

    def data(self, index: QModelIndex, role: int = ...):
        if role == Qt.ItemDataRole.DisplayRole:
            return list(self._optimizer_configurations.keys())[index.row()]
