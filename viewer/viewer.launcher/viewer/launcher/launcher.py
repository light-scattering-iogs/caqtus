import sys

from PyQt6.QtWidgets import QApplication

from analyza.loading.importers import ImageImporter, import_parameters, break_namespaces
from device.configuration import DeviceName
from sequence.runtime import Sequence
from viewer.sequence_watcher import SequenceWatcher
from viewer.single_shot_viewers import SingleShotWidget, ImageViewer, ParamsViewer

if __name__ == "__main__":
    app = QApplication(sys.argv)

    widget = SingleShotWidget(
        viewers={
            "Image 1": ImageViewer(
                importer=ImageImporter(DeviceName("Orca Quest"), "picture")
            ),
            # "Image 2": ImageViewer(
            #     importer=ImageImporter(DeviceName("Orca Quest"), "picture 2")
            # ),
            "Params": ParamsViewer(importer=import_parameters | break_namespaces),
        }
    )
    widget.show()

    watcher = SequenceWatcher(
        Sequence("2023.06_June.15.hist_check_4"),
        target=widget.add_shots,
        watch_interval=0.1,
    )
    with watcher:
        app.exec()
