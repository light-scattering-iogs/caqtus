import pytest
from PySide6.QtCore import QTimer

from caqtus.experiment_control.manager import BoundExperimentManager
from caqtus.gui.condetrol import Condetrol
from caqtus.gui.condetrol.extension import CondetrolExtension
from caqtus.session import PureSequencePath
from caqtus.session.sql import (
    Serializer,
    SQLiteExperimentSessionMaker,
)
from spincore_pulse_blaster.configuration import SpincoreSequencerConfiguration
from spincore_pulse_blaster.configuration_editor import (
    SpincorePulseBlasterDeviceConfigEditor,
)
from tests.fixtures import steps_configuration, time_lanes


@pytest.fixture
def session_maker(tmp_path):
    # url = f"sqlite:///{tmp_path / 'database.db?check_same_thread=True'}"

    serializer = Serializer.default()

    serializer.register_device_configuration(
        SpincoreSequencerConfiguration,
        SpincoreSequencerConfiguration.dump,
        SpincoreSequencerConfiguration.load,
    )

    session_maker = SQLiteExperimentSessionMaker(
        str(tmp_path / "database.db"), serializer=serializer
    )
    session_maker.create_tables()
    return session_maker


@pytest.mark.xfail
def test_condetrol(
    session_maker,
    steps_configuration,
    time_lanes,
):
    extension = CondetrolExtension()
    extension.device_extension.register_device_configuration_editor(
        SpincoreSequencerConfiguration, SpincorePulseBlasterDeviceConfigEditor
    )
    extension.device_extension.register_configuration_factory(
        "Spincore sequencer", SpincoreSequencerConfiguration.default
    )
    experiment_manager = BoundExperimentManager(session_maker, {})
    condetrol = Condetrol(
        session_maker=session_maker,
        extension=extension,
        connect_to_experiment_manager=lambda: experiment_manager,
    )
    with session_maker() as session:
        session.sequences.create(
            path=PureSequencePath(r"\test"),
            iteration_configuration=steps_configuration,
            time_lanes=time_lanes,
        )

    timer = QTimer(condetrol.window)
    timer.singleShot(0, condetrol.window.close)
    condetrol.run()
