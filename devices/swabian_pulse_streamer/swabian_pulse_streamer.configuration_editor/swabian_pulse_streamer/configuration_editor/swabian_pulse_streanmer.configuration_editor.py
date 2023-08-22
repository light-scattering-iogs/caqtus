from PyQt6.QtWidgets import QSpinBox, QFormLayout, QLineEdit

from device.configuration_editor import DeviceConfigEditor
from sequencer.configuration_editor import SequencerChannelView
from swabian_pulse_streamer.configuration import SwabianPulseStreamerConfiguration


class SpincorePulseBlasterDeviceConfigEditor(
    DeviceConfigEditor[SwabianPulseStreamerConfiguration]
):
    def __init__(
        self,
        device_config: SwabianPulseStreamerConfiguration,
        available_remote_servers,
        *args,
        **kwargs
    ):
        super().__init__(device_config, available_remote_servers, *args, **kwargs)

        self._ip_address = QLineEdit()

        self._time_step = QSpinBox()
        self._time_step.setRange(1, 1000)
        self._time_step.setSingleStep(1)
        self._time_step.setSuffix(" ns")

        self._channels_view = SequencerChannelView(device_config.channels)

        self._layout = QFormLayout()
        self._layout.addRow("IP address", self._ip_address)
        self._layout.addRow("Time step", self._time_step)
        self._layout.addRow("Channels", self._channels_view)

        self.setLayout(self._layout)

        self.update_ui(device_config)

    def get_device_config(self) -> SwabianPulseStreamerConfiguration:
        config = super().get_device_config()
        config.ip_address = self._ip_address.text()
        config.time_step = self._time_step.value()
        config.channels = self._channels_view.channel_model.channels
        return config

    def update_ui(self, device_config: SwabianPulseStreamerConfiguration):
        self._time_step.setValue(device_config.time_step)
        self._ip_address.setText(device_config.ip_address)
        self._channels_view.channel_model.channels = device_config.channels
