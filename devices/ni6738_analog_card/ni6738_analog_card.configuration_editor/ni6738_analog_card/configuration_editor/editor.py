from PyQt6.QtWidgets import QSpinBox, QFormLayout, QLineEdit

from condetrol.device_configuration_editors import DeviceConfigurationEditor
from condetrol.device_configuration_editors.sequencer_configuration_editor import (
    SequencerChannelView,
)
from core.device.sequencer.configuration import (
    AnalogChannelConfiguration,
    SoftwareTrigger,
    Constant,
)
from core.types.expression import Expression
from ni6738_analog_card.configuration import NI6738SequencerConfiguration


def get_default_ni6738_configuration() -> NI6738SequencerConfiguration:
    return NI6738SequencerConfiguration(
        remote_server="default",
        device_id="Dev0",
        time_step=2500,
        channels=tuple(
            [
                AnalogChannelConfiguration(
                    description=f"Channel {channel}",
                    output=Constant(Expression("0 V")),
                    output_unit="V",
                )
                for channel in range(NI6738SequencerConfiguration.number_channels)
            ]
        ),
        trigger=SoftwareTrigger(),
    )


class NI6738DeviceConfigEditor(DeviceConfigurationEditor[NI6738SequencerConfiguration]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._device_id = QLineEdit()

        self._time_step = QSpinBox()
        self._time_step.setRange(2500, 100000)
        self._time_step.setSingleStep(10)
        self._time_step.setSuffix(" ns")

        self.device_config = get_default_ni6738_configuration()

        self._channels_view = SequencerChannelView(self.device_config.channels)

        self._layout = QFormLayout()
        self._layout.addRow("Device id", self._device_id)
        self._layout.addRow("Time step", self._time_step)
        self._layout.addRow("Channels", self._channels_view)

        self.setLayout(self._layout)
        self.set_configuration(self.device_config)

    def set_configuration(
        self, device_configuration: NI6738SequencerConfiguration
    ) -> None:
        self._channels_view.set_channels(device_configuration.channels)
        self._time_step.setValue(device_configuration.time_step)
        self._device_id.setText(device_configuration.device_id)
        self._channels_view.channel_model.channels = device_configuration.channels
        self.device_config.remote_server = device_configuration.remote_server
        self.device_config.trigger = device_configuration.trigger

    def get_configuration(self) -> NI6738SequencerConfiguration:
        self.device_config.device_id = self._device_id.text()
        self.device_config.time_step = self._time_step.value()
        self.device_config.channels = self._channels_view.channel_model.channels
        return self.device_config
