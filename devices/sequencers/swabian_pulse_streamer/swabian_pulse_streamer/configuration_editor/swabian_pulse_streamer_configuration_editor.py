from PySide6.QtWidgets import QSpinBox, QFormLayout, QLineEdit

from caqtus.device.sequencer.configuration import (
    DigitalChannelConfiguration,
    Constant,
)
from caqtus.device.sequencer.trigger import SoftwareTrigger
from caqtus.gui.condetrol.device_configuration_editors import DeviceConfigurationEditor
from caqtus.gui.condetrol.device_configuration_editors.sequencer_configuration_editor import (
    SequencerChannelView,
)
from caqtus.types.expression import Expression
from ..configuration import SwabianPulseStreamerConfiguration


def get_default_swabian_configuration() -> SwabianPulseStreamerConfiguration:
    return SwabianPulseStreamerConfiguration(
        remote_server="default",
        ip_address="192.168.137.1",
        time_step=1,
        channels=tuple(
            [
                DigitalChannelConfiguration(
                    description=f"Channel {channel}",
                    output=Constant(Expression("Disabled")),
                )
                for channel in range(SwabianPulseStreamerConfiguration.number_channels)
            ]
        ),
        trigger=SoftwareTrigger(),
    )


class SwabianPulseStreamerDeviceConfigEditor(
    DeviceConfigurationEditor[SwabianPulseStreamerConfiguration]
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._ip_address = QLineEdit()

        self._time_step = QSpinBox()
        self._time_step.setRange(1, 1000)
        self._time_step.setSingleStep(1)
        self._time_step.setSuffix(" ns")

        self.device_config = get_default_swabian_configuration()

        self._channels_view = SequencerChannelView(self.device_config.channels)

        self._layout = QFormLayout()
        self._layout.addRow("Ip address", self._ip_address)
        self._layout.addRow("Time step", self._time_step)
        self._layout.addRow("Channels", self._channels_view)

        self.setLayout(self._layout)
        self.set_configuration(self.device_config)

    def set_configuration(
        self, device_configuration: SwabianPulseStreamerConfiguration
    ) -> None:
        self._channels_view.set_channels(device_configuration.channels)
        self._time_step.setValue(device_configuration.time_step)
        self._ip_address.setText(device_configuration.ip_address)
        self._channels_view.channel_model.channels = device_configuration.channels
        self.device_config.remote_server = device_configuration.remote_server
        self.device_config.trigger = device_configuration.trigger

    def get_configuration(self) -> SwabianPulseStreamerConfiguration:
        self.device_config.ip_address = self._ip_address.text()
        self.device_config.time_step = self._time_step.value()
        self.device_config.channels = self._channels_view.channel_model.channels
        return self.device_config
