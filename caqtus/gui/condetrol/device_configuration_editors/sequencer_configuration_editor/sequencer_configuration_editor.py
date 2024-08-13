import decimal
from typing import TypeVar, Generic, Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QSpinBox

from caqtus.device.sequencer import SequencerConfiguration, TimeStep
from ._trigger_selector import TriggerSelector
from .channels_widget import SequencerChannelWidget
from .._device_configuration_editor import FormDeviceConfigurationEditor

S = TypeVar("S", bound=SequencerConfiguration)


class SequencerConfigurationEditor(FormDeviceConfigurationEditor[S], Generic[S]):
    """A widget to edit a sequencer configuration.

    Args:
        device_configuration: The initial configuration to display.
        time_step_increment: The smallest value (in ns) by which it is possible to
            change the time step in the editor.
            Only time step that are multiple of this value can be selected0
        smallest_increment_multiple: The smallest multiple of the increment allowed.
        largest_increment_multiple: The largest multiple of the increment allowed.
        parent: The parent widget.

    Attributes:
        time_step_widget: A widget to select the time step of the sequencer.
        trigger_selector: A widget to select the trigger of the sequencer.
        channels_widget: A widget to edit the channels of the sequencer.
    """

    def __init__(
        self,
        device_configuration: S,
        time_step_increment: TimeStep,
        smallest_increment_multiple: int = 1,
        largest_increment_multiple: int = 100000,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(device_configuration, parent)

        self.time_step_widget = TimeStepEditor(
            time_step_increment, smallest_increment_multiple, largest_increment_multiple
        )
        self.form.addRow("Time step", self.time_step_widget)

        self.trigger_selector = TriggerSelector(self)
        self.trigger_selector.set_trigger(self.device_configuration.trigger)
        self.form.addRow("Trigger", self.trigger_selector)

        self.channels_widget = SequencerChannelWidget(
            self.device_configuration.channels, self
        )
        self.form.addRow("Channels", self.channels_widget)

    def get_configuration(self) -> S:
        config = super().get_configuration()
        config.time_step = self.time_step_widget.read_time_step()
        config.channels = self.channels_widget.get_channel_configurations()
        config.trigger = self.trigger_selector.get_trigger()
        return config


class TimeStepEditor(QWidget):
    def __init__(
        self,
        increment: TimeStep,
        smallest_multiple: int = 1,
        largest_multiple: int = 100000,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.increment = increment
        self.smallest_multiple = smallest_multiple
        self.largest_multiple = largest_multiple

        self.spin_box = QSpinBox()
        self.spin_box.setRange(smallest_multiple, largest_multiple)
        self.spin_box.setSuffix(format_suffix(increment))
        self.spin_box.setStepType(QSpinBox.StepType.AdaptiveDecimalStepType)
        layout.addWidget(self.spin_box)

    def set_time_step(self, time_step: TimeStep):
        div, mod = divmod(time_step, self.increment)
        if mod != 0:
            raise ValueError(
                f"Time step {time_step} is not a multiple of the increment "
                f"{self.increment}"
            )
        if not (self.smallest_multiple <= div <= self.largest_multiple):
            raise ValueError(
                f"Time step {time_step} is not between {self.smallest_multiple} and "
                f"{self.largest_multiple}"
            )

    def read_time_step(self) -> TimeStep:
        multiple = self.spin_box.value()
        return self.increment * multiple


def format_suffix(time_step: TimeStep) -> str:
    if time_step < 1:
        return f" × {time_step} ns"
    elif time_step == 1:
        return " ns"
    elif 1 < time_step < 1000:
        return f" × {time_step} ns"
    elif 1e3 <= time_step < 1e6:
        return f" × {time_step / decimal.Decimal('1e3')} µs"
    elif 1e6 <= time_step < 1e9:
        return f" × {time_step / decimal.Decimal('1e6')} ms"
    elif 1e9 <= time_step:
        return f" × {time_step / decimal.Decimal('1e9')} s"
