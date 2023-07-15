from PyQt6.QtWidgets import QSpinBox, QFormLayout

from device.configuration_editor import ConfigEditor
from spincore_sequencer.configuration import SpincoreSequencerConfiguration


class SpincorePulseBlasterConfigEditor(ConfigEditor[SpincoreSequencerConfiguration]):
    def __init__(
        self,
        device_config: SpincoreSequencerConfiguration,
        available_remote_servers,
        *args,
        **kwargs
    ):
        super().__init__(device_config, available_remote_servers, *args, **kwargs)

        self._board_number = QSpinBox()
        self._board_number.setRange(0, 100)
        self._board_number.setValue(device_config.board_number)

        self._time_step = QSpinBox()
        self._time_step.setRange(50, 1000)
        self._time_step.setValue(device_config.time_step)
        self._time_step.setSingleStep(10)
        self._time_step.setSuffix(" ns")

        self._layout = QFormLayout()
        self._layout.addRow("Board number", self._board_number)
        self._layout.addRow("Time step", self._time_step)

        self.setLayout(self._layout)

    def get_device_config(self) -> SpincoreSequencerConfiguration:
        config = super().get_device_config()
        config.board_number = self._board_number.value()
        config.time_step = self._time_step.value()
        return config

