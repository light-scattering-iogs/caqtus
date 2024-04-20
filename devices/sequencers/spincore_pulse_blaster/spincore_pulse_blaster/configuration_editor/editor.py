from PySide6.QtWidgets import QSpinBox

from caqtus.gui.condetrol.device_configuration_editors import (
    SequencerConfigurationEditor,
)
from ..configuration import SpincoreSequencerConfiguration


class SpincorePulseBlasterDeviceConfigEditor(
    SequencerConfigurationEditor[SpincoreSequencerConfiguration]
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.time_step_spinbox.setRange(50, 1000)

        self._board_number = QSpinBox()
        self._board_number.setRange(0, 100)
        self.form.insertRow(1, "Board number", self._board_number)

    def get_configuration(self) -> SpincoreSequencerConfiguration:
        config = super().get_configuration()
        config.board_number = self._board_number.value()
        return config
