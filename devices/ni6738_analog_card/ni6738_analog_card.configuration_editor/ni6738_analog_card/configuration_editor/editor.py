from typing import Collection

from PyQt6.QtWidgets import QLineEdit, QDoubleSpinBox, QFormLayout

from device.configuration_editor import DeviceConfigEditor
from device_server.name import DeviceServerName
from ni6738_analog_card.configuration import NI6738SequencerConfiguration
from sequencer.configuration_editor import SequencerChannelView


class NI6738AnalogCardConfigEditor(DeviceConfigEditor[NI6738SequencerConfiguration]):
    def __init__(
        self,
        device_config: NI6738SequencerConfiguration,
        available_remote_servers: Collection[DeviceServerName],
        *args,
        **kwargs
    ):
        super().__init__(device_config, available_remote_servers, *args, **kwargs)

        self._device_id = QLineEdit()

        self._time_step = QDoubleSpinBox()
        self._time_step.setRange(2.5, 1000)
        self._time_step.setSingleStep(0.1)
        self._time_step.setSuffix(" µs")

        self._channels_view = SequencerChannelView(device_config.channels)

        self._layout = QFormLayout()
        self._layout.addRow("Device id", self._device_id)
        self._layout.addRow("Time step", self._time_step)
        self._layout.addRow("Channels", self._channels_view)

        self.setLayout(self._layout)

        self.update_ui(device_config)

    def get_device_config(self) -> NI6738SequencerConfiguration:
        config = super().get_device_config()
        config.device_id = self._device_id.text()
        config.time_step = round(self._time_step.value() * 1e3)
        config.channels = self._channels_view.channel_model.channels
        return config

    def update_ui(self, device_config: NI6738SequencerConfiguration):
        self._time_step.setValue(device_config.time_step / 1e3)
        self._device_id.setText(device_config.device_id)
        self._channels_view.channel_model.channels = device_config.channels
