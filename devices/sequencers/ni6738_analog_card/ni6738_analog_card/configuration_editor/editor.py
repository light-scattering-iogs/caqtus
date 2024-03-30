from PySide6.QtWidgets import QLineEdit

from caqtus.gui.condetrol.device_configuration_editors import (
    SequencerConfigurationEditor,
)
from ..configuration import NI6738SequencerConfiguration


class NI6738DeviceConfigEditor(
    SequencerConfigurationEditor[NI6738SequencerConfiguration]
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.time_step_spinbox.setRange(2500, 100000)

        self._device_id = QLineEdit()
        self.form.insertRow(1, "Device id", self._device_id)
        self._device_id.setText(self.device_configuration.device_id)

    def get_configuration(self) -> NI6738SequencerConfiguration:
        config = super().get_configuration()
        config.device_id = self._device_id.text()
        return config
