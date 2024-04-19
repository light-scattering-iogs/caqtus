from typing import TypeVar, Generic, Optional

from PySide6.QtWidgets import QWidget, QSpinBox

from caqtus.device.sequencer import SequencerConfiguration
from .channel_view import SequencerChannelView
from ..device_configuration_editor import FormDeviceConfigurationEditor

S = TypeVar("S", bound=SequencerConfiguration)


class SequencerConfigurationEditor(FormDeviceConfigurationEditor[S], Generic[S]):
    def __init__(self, device_configuration: S, parent: Optional[QWidget] = None):
        super().__init__(device_configuration, parent)

        self.time_step_spinbox = QSpinBox(self)
        self.time_step_spinbox.setRange(0, 100000)
        self.time_step_spinbox.setSuffix(" ns")
        self.form.addRow("Time step", self.time_step_spinbox)
        self.time_step_spinbox.setValue(self.device_configuration.time_step)

        self._channels_view = SequencerChannelView(self.device_configuration.channels)
        self.form.addRow("Channels", self._channels_view)

    def get_configuration(self) -> S:
        config = super().get_configuration()
        config.time_step = self.time_step_spinbox.value()
        config.channels = self._channels_view.channel_model.channels
        return config
