from typing import Optional

from PyQt6.QtWidgets import QWidget, QVBoxLayout

from experiment_config import ExperimentConfig
from siglent_sdg6000x.configuration import (
    SiglentSDG6000XConfiguration,
    SineWaveConfiguration,
    SiglentSDG6000XChannelConfiguration,
)
from .channel_editor_ui import Ui_ChannelEditor
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
        self.channel_editors: list[ChannelEditor] = []

        self.setup_server_combobox()
        self.setup_visa_resource()
        self.setup_channels()
        # self.setup_waveforms()

    def setup_server_combobox(self):
        for remote_server in self.config.device_servers:
            self.remote_server_combobox.addItem(remote_server)
        self.remote_server_combobox.setCurrentText(self.siglent_config.remote_server)

    def setup_visa_resource(self):
        self.visa_resource_lineedit.setText(self.siglent_config.visa_resource)

    def setup_channels(self):
        for index in range(self.siglent_config.channel_number):
            editor = ChannelEditor()
            editor.setup(self.siglent_config.channel_configurations[index])
            self.channel_editors.append(editor)

        layout_1 = QVBoxLayout()
        layout_1.addWidget(self.channel_editors[0])
        self.tab_1.setLayout(layout_1)

        layout_2 = QVBoxLayout()
        layout_2.addWidget(self.channel_editors[1])
        self.tab_2.setLayout(layout_2)

    @staticmethod
    def setup_waveform(
        editor: "ChannelEditor", config: SiglentSDG6000XChannelConfiguration
    ):
        editor.waveform_combobox.addItem("Sine")
        editor.waveform_combobox.setCurrentText("Sine")
        editor.parameters_layout

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

    @staticmethod
    def setup_sine_editor(editor: "SineEditor", config: SineWaveConfiguration):
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
        self.read_visa_resource()
        self.read_channels()
        # self.read_waveforms()
        self.config.set_device_config(self.device_name, self.siglent_config)
        return self.config

    def read_server_combobox(self):
        self.siglent_config.remote_server = self.remote_server_combobox.currentText()

    def read_visa_resource(self):
        self.siglent_config.visa_resource = self.visa_resource_lineedit.text()

    def read_channels(self):
        for index in range(self.siglent_config.channel_number):
            self.siglent_config.channel_configurations[index] = self.channel_editors[
                index
            ].get_updated_config(self.siglent_config.channel_configurations[index])

    @staticmethod
    def read_channel(
        editor: "ChannelEditor", config: SiglentSDG6000XChannelConfiguration
    ):
        config.output_enabled = editor.on_button.isChecked()
        if editor.output_load_combobox.currentText() == "HiZ":
            config.output_load = "HZ"
        elif editor.output_load_combobox.currentText() == "50 Ω":
            config.output_load = 50.0
        else:
            raise NotImplementedError()
        return config

    def read_waveforms(self):
        for index in range(self.siglent_config.channel_number):
            self.siglent_config.waveform_configs[index] = self.read_sine_waveform(
                self.waveform_editors[index],
                self.siglent_config.waveform_configs[index],
            )

    @staticmethod
    def read_sine_waveform(editor: "SineEditor", config: SineWaveConfiguration):
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


class ChannelEditor(QWidget, Ui_ChannelEditor):
    def __init__(self, *args):
        super().__init__(*args)
        self.setupUi(self)

    def setup(self, config: SiglentSDG6000XChannelConfiguration):
        self.on_button.setChecked(config.output_enabled)
        self.off_button.setChecked(not config.output_enabled)

        self.output_load_combobox.addItem("50 Ω")
        self.output_load_combobox.addItem("HiZ")
        if config.output_load == 50.0:
            self.output_load_combobox.setCurrentText("50 Ω")
        elif config.output_load == "HZ":
            self.output_load_combobox.setCurrentText("HiZ")
        else:
            raise NotImplemented(
                f"output load of {config.output_load} Ω not implemented"
            )
        SiglentSDG6000XConfigEditor.setup_waveform(self, config)

    def get_updated_config(
        self, config: SiglentSDG6000XChannelConfiguration
    ) -> SiglentSDG6000XChannelConfiguration:
        config.output_enabled = self.on_button.isChecked()
        if self.output_load_combobox.currentText() == "HiZ":
            config.output_load = "HZ"
        elif self.output_load_combobox.currentText() == "50 Ω":
            config.output_load = 50.0
        else:
            raise NotImplementedError()
        return config
