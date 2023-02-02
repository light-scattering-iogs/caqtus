from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout

from experiment_config import ExperimentConfig
from siglent_sdg6000x.configuration import (
    SiglentSDG6000XConfiguration,
    SineWaveConfiguration,
    SiglentSDG6000XChannelConfiguration,
    AmplitudeModulationConfiguration,
    FrequencyModulationConfiguration,
)
from .amplitude_modulation_editor_ui import Ui_AmplitudeModulationEditor
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


class SineEditor(QWidget, Ui_SineEditor):
    def __init__(self, *args):
        super().__init__(*args)
        self.setupUi(self)

    def setup(self, config: SineWaveConfiguration):
        self.frequency_name_lineedit.setText(config.frequency.name)
        self.frequency_expression_lineedit.setText(config.frequency.expression.body)

        self.amplitude_name_lineedit.setText(config.amplitude.name)
        self.amplitude_expression_lineedit.setText(config.amplitude.expression.body)

        self.offset_name_lineedit.setText(config.offset.name)
        self.offset_expression_lineedit.setText(config.offset.expression.body)

        self.phase_name_lineedit.setText(config.phase.name)
        self.phase_expression_lineedit.setText(config.phase.expression.body)

    def get_updated_config(self, config: SineWaveConfiguration):
        config.frequency.name = self.frequency_name_lineedit.text()
        config.frequency.expression.body = self.frequency_expression_lineedit.text()

        config.amplitude.name = self.amplitude_name_lineedit.text()
        config.amplitude.expression.body = self.amplitude_expression_lineedit.text()

        config.offset.name = self.offset_name_lineedit.text()
        config.offset.expression.body = self.offset_expression_lineedit.text()

        config.phase.name = self.phase_name_lineedit.text()
        config.phase.expression.body = self.phase_expression_lineedit.text()
        return config


class AmplitudeModulationEditor(QWidget, Ui_AmplitudeModulationEditor):
    def __init__(self, *args):
        super().__init__(*args)
        self.setupUi(self)

    def setup(self, config: AmplitudeModulationConfiguration):
        self.source_combobox.addItem("INT")
        self.source_combobox.addItem("EXT")
        self.source_combobox.addItem("CH1")
        self.source_combobox.addItem("CH2")
        self.source_combobox.setCurrentText(config.source)

        self.depth_spinbox.setValue(int(config.depth))


class ChannelEditor(QWidget, Ui_ChannelEditor):
    def __init__(self, *args):
        super().__init__(*args)
        self.setupUi(self)
        self.waveform_editor = SineEditor()
        self.modulation_editor: Optional[AmplitudeModulationEditor] = None

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
        self.setup_waveform(config)
        self.setup_modulation(config)

    def setup_waveform(self, config: SiglentSDG6000XChannelConfiguration):
        self.waveform_combobox.addItem("Sine")
        self.waveform_combobox.setCurrentText("Sine")
        self.parameters_layout.setAlignment(
            self.waveform_label, Qt.AlignmentFlag.AlignTop
        )
        self.parameters_layout.setAlignment(
            self.waveform_combobox, Qt.AlignmentFlag.AlignTop
        )
        self.parameters_layout.addWidget(
            self.waveform_editor, 2, 2, alignment=Qt.AlignmentFlag.AlignTop
        )
        self.waveform_editor.setup(config.waveform)

    def setup_modulation(self, config: SiglentSDG6000XChannelConfiguration):
        self.parameters_layout.setAlignment(
            self.modulation_label, Qt.AlignmentFlag.AlignTop
        )
        self.parameters_layout.setAlignment(
            self.modulation_combobox, Qt.AlignmentFlag.AlignTop
        )
        self.modulation_combobox.addItem("None")
        self.modulation_combobox.addItem("AM")
        self.modulation_combobox.addItem("FM")
        if config.modulation is None:
            self.modulation_combobox.setCurrentText("None")
        elif isinstance(config.modulation, AmplitudeModulationConfiguration):
            self.modulation_combobox.setCurrentText("AM")
            self.modulation_editor = AmplitudeModulationEditor()
            self.modulation_editor.setup(config.modulation)
            self.parameters_layout.addWidget(
                self.modulation_editor, 3, 2, alignment=Qt.AlignmentFlag.AlignTop
            )
        elif isinstance(config.modulation, FrequencyModulationConfiguration):
            self.modulation_combobox.setCurrentText("FM")
        else:
            raise NotImplementedError()

    #     self.modulation_combobox.currentTextChanged.connect(self.on_modulation_combobox_current_text_changed)
    #
    # def on_modulation_combobox_current_text_changed(self, text: str):
    #     pass

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

        config.waveform = self.waveform_editor.get_updated_config(config.waveform)
        return config
