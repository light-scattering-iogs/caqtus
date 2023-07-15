from PyQt6.QtWidgets import QSpinBox, QFormLayout

from device.configuration_editor import DeviceConfigEditor
from sequencer.configuration_editor import SequencerChannelView
from spincore_sequencer.configuration import SpincoreSequencerConfiguration


class SpincorePulseBlasterDeviceConfigEditor(DeviceConfigEditor[SpincoreSequencerConfiguration]):

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

        self._time_step = QSpinBox()
        self._time_step.setRange(50, 1000)
        self._time_step.setSingleStep(10)
        self._time_step.setSuffix(" ns")

        self._channels_view = SequencerChannelView(device_config.channels)

        self._layout = QFormLayout()
        self._layout.addRow("Board number", self._board_number)
        self._layout.addRow("Time step", self._time_step)
        self._layout.addRow("Channels", self._channels_view)

        self.setLayout(self._layout)

        self.update_ui(device_config)

    def get_device_config(self) -> SpincoreSequencerConfiguration:
        config = super().get_device_config()
        config.board_number = self._board_number.value()
        config.time_step = self._time_step.value()
        config.channels = self._channels_view.channel_model.channels
        return config

    def update_ui(self, device_config: SpincoreSequencerConfiguration):
        self._time_step.setValue(device_config.time_step)
        self._board_number.setValue(device_config.board_number)
        self._channels_view.channel_model.channels = device_config.channels

