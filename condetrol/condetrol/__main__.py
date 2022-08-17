import sys

from PyQt5.QtWidgets import QApplication

from experiment_viewer import ExperimentViewer

if __name__ == "__main__":
    app = QApplication(sys.argv)
    experiment_viewer = ExperimentViewer()
    experiment_viewer.show()
    app.exec()
