import sys

import sqlalchemy
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

import qdarktheme
from condetrol import CondetrolMainWindow
from core.experiment.manager import ExperimentManager
from core.experiment.manager import RemoteExperimentManagerClient
from core.session.sql import (
    SQLExperimentSessionMaker,
    create_tables,
    default_serializer,
)
from elliptec_ell14.configuration import ElliptecELL14RotationStageConfiguration
from elliptec_ell14.configuration_editor import (
    ElliptecELL14RotationStageConfigurationEditor,
)
from orca_quest.configuration import OrcaQuestCameraConfiguration
from orca_quest.configuration_editor import OrcaQuestConfigurationEditor
from spincore_sequencer.configuration import SpincoreSequencerConfiguration
from spincore_sequencer.configuration_editor import (
    SpincorePulseBlasterDeviceConfigEditor,
)


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == "__main__":
    sys.excepthook = except_hook

    app = QApplication(sys.argv)
    app.setOrganizationName("Caqtus")
    app.setApplicationName("Condetrol")
    qdarktheme.setup_theme(theme="dark")
    engine = sqlalchemy.create_engine("sqlite:///database.db")
    create_tables(engine)
    session_maker = SQLExperimentSessionMaker(
        engine,
        {
            "ElliptecELL14RotationStageConfiguration": {
                "dumper": ElliptecELL14RotationStageConfiguration.dump,
                "loader": ElliptecELL14RotationStageConfiguration.load,
            },
            "SpincoreSequencerConfiguration": {
                "dumper": SpincoreSequencerConfiguration.dump,
                "loader": SpincoreSequencerConfiguration.load,
            },
            "OrcaQuestCameraConfiguration": {
                "dumper": OrcaQuestCameraConfiguration.dump,
                "loader": OrcaQuestCameraConfiguration.load,
            },
        },
        serializer=default_serializer,
    )

    font = QFont("Arial")
    font.setPointSize(10)
    app.setFont(font)

    def connect_to_experiment_manager() -> ExperimentManager:
        client = RemoteExperimentManagerClient(
            address=("localhost", 60000),
            authkey=b"Deardear",
        )
        return client.get_experiment_manager()

    with CondetrolMainWindow(
        session_maker,
        {
            "ElliptecELL14RotationStageConfiguration": {
                "editor_type": ElliptecELL14RotationStageConfigurationEditor
            },
            "SpincoreSequencerConfiguration": {
                "editor_type": SpincorePulseBlasterDeviceConfigEditor
            },
            "OrcaQuestCameraConfiguration": {
                "editor_type": OrcaQuestConfigurationEditor
            },
        },
        connect_to_experiment_manager=connect_to_experiment_manager,
    ) as main_window:
        main_window.show()
        app.exec()
