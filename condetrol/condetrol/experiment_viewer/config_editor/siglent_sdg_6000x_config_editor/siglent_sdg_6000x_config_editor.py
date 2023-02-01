from typing import Optional

from PyQt5.QtWidgets import QWidget, QVBoxLayout

from experiment_config import ExperimentConfig
from siglent_sdg6000x.configuration import (
    SiglentSDG6000XConfiguration,
    SineWaveConfiguration,
)
from .editor_widget_ui import Ui_EditorWidget
from .sine_editor_ui import Ui_SineEditor
from ..config_settings_editor import ConfigSettingsEditor


class SiglentSDG6000XConfigEditor(ConfigSettingsEditor, Ui_EditorWidget):
    def __init__(
        self,
        experiment_config: ExperimentConfig,
        tree_label: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(experiment_config, tree_label, parent)
        self.setupUi(self)

        self.config = experiment_config
        self.device_name = self.strip_device_prefix(tree_label)
        self.siglent_config: SiglentSDG6000XConfiguration = (
            self.config.get_device_config(self.device_name)
        )

        self.waveform_editors = []

        self.setup_server_combobox()
        self.setup_waveforms()

    def setup_server_combobox(self):
        for remote_server in self.config.device_servers:
            self.remote_server_combobox.addItem(remote_server)
        self.remote_server_combobox.setCurrentText(self.siglent_config.remote_server)

    def setup_waveforms(self):
        self.waveform_editors = []
        for channel in range(self.siglent_config.channel_number):
            editor = SineEditor()
            self.setup_sine_editor(
                editor, self.siglent_config.waveform_configs[channel]
            )
            self.waveform_editors.append(editor)
        layout_1 = QVBoxLayout()
        layout_1.addWidget(self.waveform_editors[0])
        self.tab_1.setLayout(layout_1)

        layout_2 = QVBoxLayout()
        layout_2.addWidget(self.waveform_editors[1])
        self.tab_2.setLayout(layout_2)

    def setup_sine_editor(self, editor: "SineEditor", config: SineWaveConfiguration):
        editor.frequency_name_lineedit.setText(config.frequency.name)
        editor.frequency_expression_lineedit.setText(config.frequency.expression.body)

        editor.amplitude_name_lineedit.setText(config.amplitude.name)
        editor.amplitude_expression_lineedit.setText(config.amplitude.expression.body)

        editor.offset_name_lineedit.setText(config.offset.name)
        editor.offset_expression_lineedit.setText(config.offset.expression.body)

        editor.phase_name_lineedit.setText(config.phase.name)
        editor.phase_expression_lineedit.setText(config.phase.expression.body)
        return editor

    def get_experiment_config(self) -> ExperimentConfig:
        self.read_server_combobox()
        self.read_waveforms()
        self.config.set_device_config(self.device_name, self.siglent_config)
        return self.config

    def read_server_combobox(self):
        self.siglent_config.remote_server = self.remote_server_combobox.currentText()

    def read_waveforms(self):
        for index in range(self.siglent_config.channel_number):
            self.siglent_config.waveform_configs[index] = self.read_sine_waveform(
                self.waveform_editors[index],
                self.siglent_config.waveform_configs[index],
            )

    def read_sine_waveform(self, editor: "SineEditor", config: SineWaveConfiguration):
        config.frequency.name = editor.frequency_name_lineedit.text()
        config.frequency.expression.body = editor.frequency_expression_lineedit.text()

        config.amplitude.name = editor.amplitude_name_lineedit.text()
        config.amplitude.expression.body = editor.amplitude_expression_lineedit.text()

        config.offset.name = editor.offset_name_lineedit.text()
        config.offset.expression.body = editor.offset_expression_lineedit.text()

        config.phase.name = editor.phase_name_lineedit.text()
        config.phase.expression.body = editor.phase_expression_lineedit.text()
        return config


class SineEditor(QWidget, Ui_SineEditor):
    def __init__(self, *args):
        super().__init__(*args)
        self.setupUi(self)
