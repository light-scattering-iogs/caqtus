from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStyledItemDelegate, QDialog, QWidget, QVBoxLayout
from condetrol.device_configuration_editors.sequencer_configuration_editor.channel_output_editor import \
    OutputConstructionError
from core.device.sequencer import ChannelConfiguration
from exception_tree import ExceptionDialog

from .channel_output_editor import ChannelOutputEditor
from .dialog_ui import Ui_ChannelOutputDialog
from ...logger import logger


class ChannelOutputDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = ChannelOutputDialog(parent)
        return editor

    def setEditorData(self, editor, index):
        assert isinstance(editor, ChannelOutputDialog)
        channel_index = index.row()
        channel_configuration = index.data(role=Qt.ItemDataRole.EditRole)
        assert isinstance(channel_configuration, ChannelConfiguration)
        editor.setWindowTitle(
            f"Edit channel {channel_index}: {channel_configuration.description}..."
        )
        logger.debug(
            "Starting editing channel configuration: %r", channel_configuration
        )
        editor.set_channel_output(index.data(role=Qt.ItemDataRole.EditRole))

    def setModelData(self, editor, model, index):
        assert isinstance(editor, ChannelOutputDialog)
        if editor.result() == QDialog.DialogCode.Accepted:
            channel_configuration = editor.get_channel_configuration()
            logger.debug(
                "Finished editing channel configuration: %r",
                channel_configuration,
            )


class ChannelOutputDialog(QDialog, Ui_ChannelOutputDialog):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setWindowTitle("Channel Output")
        self.setModal(True)
        self.setupUi(self)
        self.show()

    def set_channel_output(self, channel_configuration: ChannelConfiguration):
        self.view = ChannelOutputEditor("test", channel_configuration)
        layout = self.layout()
        assert isinstance(layout, QVBoxLayout)
        layout.insertWidget(0, self.view)

    def get_channel_configuration(self) -> ChannelConfiguration:
        return self.view.get_channel_configuration()

    def accept(self) -> None:
        # When the user presses the OK button, we try to construct the channel
        # output from the scene.
        # If it fails, we display an exception dialog and cancel the accept action.
        try:
            self.get_channel_configuration()
        except OutputConstructionError as e:
            exception_dialog = ExceptionDialog(self)
            exception_dialog.set_exception(e)
            exception_dialog.set_message(
                "Failed to construct channel output from scene."
            )
            exception_dialog.exec()
        else:
            super().accept()

