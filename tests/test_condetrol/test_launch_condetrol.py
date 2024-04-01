import pytest
from PySide6.QtCore import QTimer

from caqtus.gui.condetrol import Condetrol
from caqtus.session.sql import (
    SQLExperimentSessionMaker,
    Serializer,
    default_sequence_serializer,
)


@pytest.fixture
def session_maker(tmp_path):
    url = f"sqlite:///{tmp_path / 'database.db'}"

    session_maker = SQLExperimentSessionMaker.from_url(
        url,
        serializer=Serializer(
            device_configuration_serializers={},
            sequence_serializer=default_sequence_serializer,
        ),
    )
    session_maker.create_tables()
    return session_maker


def test_condetrol(session_maker):
    condetrol = Condetrol(session_maker=session_maker)
    timer = QTimer(condetrol.window)
    timer.singleShot(0, condetrol.window.close)
    condetrol.run()
