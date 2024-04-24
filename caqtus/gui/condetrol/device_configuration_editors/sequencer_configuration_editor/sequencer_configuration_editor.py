from typing import TypeVar, Generic, Optional

from PySide6.QtWidgets import QWidget, QSpinBox

from caqtus.device.sequencer import SequencerConfiguration
from .channels_widget import SequencerChannelWidget
from ..device_configuration_editor import FormDeviceConfigurationEditor
from ._trigger_selector import TriggerSelector

S = TypeVar("S", bound=SequencerConfiguration)


class SequencerConfigurationEditor(FormDeviceConfigurationEditor[S], Generic[S]):
    """A widget to edit a sequencer configuration.

    Attributes:
        time_step_spinbox: A spinbox to edit the time step of the sequencer.
        trigger_selector: A widget to select the trigger of the sequencer.
        channels_widget: A widget to edit the channels of the sequencer.
    """

    def __init__(self, device_configuration: S, parent: Optional[QWidget] = None):
        super().__init__(device_configuration, parent)

        self.time_step_spinbox = QSpinBox(self)
        self.time_step_spinbox.setRange(0, 100000)
        self.time_step_spinbox.setSuffix(" ns")
        self.form.addRow("Time step", self.time_step_spinbox)
        self.time_step_spinbox.setValue(self.device_configuration.time_step)

        self.trigger_selector = TriggerSelector(self)
        self.trigger_selector.set_trigger(self.device_configuration.trigger)
        self.form.addRow("Trigger", self.trigger_selector)

        self.channels_widget = SequencerChannelWidget(
            self.device_configuration.channels, self
        )
        self.form.addRow("Channels", self.channels_widget)

    def get_configuration(self) -> S:
        config = super().get_configuration()
        config.time_step = self.time_step_spinbox.value()
        config.channels = self.channels_widget.get_channel_configurations()
        config.trigger = self.trigger_selector.get_trigger()
        return config
