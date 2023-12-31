from PyQt6.QtWidgets import QSpinBox, QFormLayout

from condetrol.device_configuration_editors import DeviceConfigurationEditor
from condetrol.device_configuration_editors.sequencer_configuration_editor import (
    SequencerChannelView,
)
from core.device.sequencer.configuration import (
    DigitalChannelConfiguration,
    DigitalMapping,
    SoftwareTrigger,
)
from spincore_sequencer.configuration import SpincoreSequencerConfiguration


def get_default_spincore_configuration() -> SpincoreSequencerConfiguration:
    return SpincoreSequencerConfiguration(
        board_number=0,
        time_step=50,
        channels=tuple(
            [
                DigitalChannelConfiguration(
                    description=None,
                    output_mapping=DigitalMapping(invert=False),
                    default_value=False,
                    color=None,
                    delay=0.0,
                )
                for _ in range(SpincoreSequencerConfiguration.number_channels)
            ]
        ),
        trigger=SoftwareTrigger(),
    )


class SpincorePulseBlasterDeviceConfigEditor(
    DeviceConfigurationEditor[SpincoreSequencerConfiguration]
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._board_number = QSpinBox()
        self._board_number.setRange(0, 100)

        self._time_step = QSpinBox()
        self._time_step.setRange(50, 1000)
        self._time_step.setSingleStep(10)
        self._time_step.setSuffix(" ns")

        self.device_config = get_default_spincore_configuration()

        self._channels_view = SequencerChannelView(self.device_config.channels)

        self._layout = QFormLayout()
        self._layout.addRow("Board number", self._board_number)
        self._layout.addRow("Time step", self._time_step)
        self._layout.addRow("Channels", self._channels_view)

        self.setLayout(self._layout)

    def set_configuration(
        self, device_configuration: SpincoreSequencerConfiguration
    ) -> None:
        self._channels_view.set_channels(device_configuration.channels)
        self._time_step.setValue(device_configuration.time_step)
        self._board_number.setValue(device_configuration.board_number)
        self._channels_view.channel_model.channels = device_configuration.channels

    def get_configuration(self) -> SpincoreSequencerConfiguration:
        self.device_config.board_number = self._board_number.value()
        self.device_config.time_step = self._time_step.value()
        self.device_config.channels = self._channels_view.channel_model.channels
        return self.device_config
