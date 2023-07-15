import sys
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication

from experiment.configuration import ExperimentConfig
from sequencer.configuration_editor import SequencerChannelView


@pytest.fixture
def experiment_config():
    path = Path(__file__).parent / "experiment_config.yaml"
    with open(path, "r") as file:
        config = ExperimentConfig.from_yaml(file.read())
    return config


def test_show(experiment_config: ExperimentConfig):
    def except_hook(cls, exception, traceback):
        sys.__excepthook__(cls, exception, traceback)

    sys.excepthook = except_hook
    app = QApplication(sys.argv)
    device_config = experiment_config.get_device_config(
        "Spincore PulseBlaster sequencer"
    )
    widget = SequencerChannelView(device_config.channels)

    widget.show()
    app.exec()
