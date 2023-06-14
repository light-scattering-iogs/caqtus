import sys

from PyQt6.QtWidgets import QApplication

from analyza.loading.importers import ImageImporter
from device.configuration import DeviceName
from experiment.session import get_standard_experiment_session
from sequence.runtime import Sequence
from viewer.single_shot_viewers import ImageViewer

if __name__ == "__main__":
    app = QApplication(sys.argv)

    session = get_standard_experiment_session()
    sequence = Sequence("2023.06_June.14.survival_138_5")
    with session.activate():
        shots = sequence.get_shots(session)

    viewer = ImageViewer(importer=ImageImporter(DeviceName("Orca Quest"), "picture"))
    viewer.set_shot(shots[0])
    viewer.show()
    app.exec()
