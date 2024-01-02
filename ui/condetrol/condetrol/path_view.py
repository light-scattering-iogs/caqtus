import functools

from PyQt6 import QtCore
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu, QMessageBox, QInputDialog, QLineEdit

from core.session import ExperimentSessionMaker, PureSequencePath
from core.session.result import unwrap
from sequence_hierarchy import PathHierarchyView
from .app_name import APPLICATION_NAME


class EditablePathHierarchyView(PathHierarchyView):
    def __init__(self, session_maker: ExperimentSessionMaker, parent=None):
        super().__init__(session_maker, parent)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)  # type: ignore

    def show_context_menu(self, pos):
        index = self.indexAt(pos)

        path = self._model.get_path(self._proxy_model.mapToSource(index))

        menu = QMenu(self)

        with self.session_maker() as session:
            is_sequence = unwrap(session.sequence_collection.is_sequence(path))
        if not is_sequence:
            new_menu = QMenu("New...")
            menu.addMenu(new_menu)

            create_folder_action = QAction("folder")
            new_menu.addAction(create_folder_action)
            create_folder_action.triggered.connect(
                functools.partial(self.create_new_folder, path)
            )

            if not path.is_root():
                delete_action = QAction("Delete")
                menu.addAction(delete_action)
                delete_action.triggered.connect(functools.partial(self.delete, path))

        menu.exec(self.mapToGlobal(pos))

    def create_new_folder(self, path: PureSequencePath):
        text, ok = QInputDialog().getText(
            self,
            f"New folder in {path}...",
            "Folder name:",
            QLineEdit.EchoMode.Normal,
            "new_folder",
        )
        if ok and text:
            new_path = path / text
            with self.session_maker() as session:
                session.sequence_hierarchy.create_path(new_path)

    def delete(self, path: PureSequencePath):
        message = (
            f'You are about to delete the path "{path}".\n'
            "All data inside will be irremediably lost."
        )
        if self.exec_confirmation_message_box(message):
            with self.session_maker() as session:
                if session.sequence_collection.is_sequence(path):
                    session.sequence_hierarchy.delete_path(path, delete_sequences=True)
                else:
                    # An error will be raised if someone tries to delete a folder that
                    # contains sequences.
                    session.sequence_hierarchy.delete_path(path, delete_sequences=False)

    def exec_confirmation_message_box(self, message: str) -> bool:
        """Show a popup box to ask  a question."""

        message_box = QMessageBox(self)
        message_box.setWindowTitle(APPLICATION_NAME)
        message_box.setText(message)
        message_box.setInformativeText("Are you really sure you want to continue?")
        message_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        message_box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        message_box.setIcon(QMessageBox.Icon.Warning)
        result = message_box.exec()
        if result == QMessageBox.StandardButton.Cancel:
            return False
        return True
