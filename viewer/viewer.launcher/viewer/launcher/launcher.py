import sys

from PyQt6.QtWidgets import QApplication

from analyza.loading.importers import ImageImporter, import_parameters, break_namespaces
from device.configuration import DeviceName
from experiment.session import get_standard_experiment_session_maker
from sequence.runtime import Sequence
from viewer.sequence_watcher import SequenceWatcher
from viewer.single_shot_viewers import SingleShotWidget, ImageViewer, ParamsViewer
import qdarkstyle

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(qdarkstyle.load_stylesheet())

    widget = SingleShotWidget(
        viewers={
            "Image 1": ImageViewer(
                importer=ImageImporter(DeviceName("Orca Quest"), "picture")
            ),
            "Image 2": ImageViewer(
                importer=ImageImporter(DeviceName("Orca Quest"), "background")
            ),
            "Params": ParamsViewer(importer=import_parameters | break_namespaces),
        },
        experiment_session_maker=get_standard_experiment_session_maker(),
    )
    widget.show()


    app.exec()
