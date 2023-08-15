import logging
import sys

import qdarkstyle
from PyQt6.QtWidgets import QApplication

import serialization
from analyza.loading.importers import (
    ImageLoader,
    import_parameters,
    break_namespaces,
    AtomsImporter,
)
from device.configuration import DeviceName
from experiment.session import get_standard_experiment_session_maker
from viewer.single_shot_viewers import (
    SingleShotWidget,
    ImageViewer,
    ParamsViewer,
    AtomsViewer,
)

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(qdarkstyle.load_stylesheet())

    viewer = ImageViewer(importer=ImageLoader(DeviceName("Orca Quest"), "picture 3"))
    print(serialization.converters["yaml"].dumps(viewer))

    widget = SingleShotWidget(
        viewers={
            "Image 3": viewer,
            "Atoms 3": AtomsViewer(
                importer=AtomsImporter(DeviceName("Atom detector"), "picture 3")
            ),
            "Image 2": ImageViewer(
                importer=ImageLoader(DeviceName("Orca Quest"), "picture 2")
            ),
            "Atoms 2": AtomsViewer(
                importer=AtomsImporter(DeviceName("Atom detector"), "picture 2")
            ),
            "Image 1": ImageViewer(
                importer=ImageLoader(DeviceName("Orca Quest"), "picture 1")
            ),
            "Atoms 1": AtomsViewer(
                importer=AtomsImporter(DeviceName("Atom detector"), "picture 1")
            ),
            "Params": ParamsViewer(importer=import_parameters | break_namespaces),
        },
        experiment_session_maker=get_standard_experiment_session_maker(),
    )
    widget.show()

    app.exec()
