from PyQt6.QtCore import pyqtSignal, QTimer, Qt, QModelIndex
from PyQt6.QtWidgets import QTreeView

from core.session import ExperimentSessionMaker
from core.session.sequence import Sequence
from sequence_hierarchy import SequenceHierarchyModel, SequenceHierarchyDelegate


class SequenceHierarchyWidget(QTreeView):
    sequence_double_clicked = pyqtSignal(Sequence)

    def __init__(self, session_maker: ExperimentSessionMaker, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._session_maker = session_maker
        self._sequence_hierarchy_model = SequenceHierarchyModel(session_maker)
        self.setModel(self._sequence_hierarchy_model)
        self.setItemDelegateForColumn(1, SequenceHierarchyDelegate())
        self.doubleClicked.connect(self.on_double_clicked)  # type:ignore

        # refresh the view to update the info in real time
        self._view_update_timer = QTimer(self)
        self._view_update_timer.timeout.connect(self.update)  # type: ignore
        self._view_update_timer.setTimerType(Qt.TimerType.CoarseTimer)
        self._view_update_timer.start(500)

    def on_double_clicked(self, index: QModelIndex) -> None:
        path = self._sequence_hierarchy_model.get_path(index)
        if path is None:
            return
        with self._session_maker() as session:
            if path.is_sequence(session):
                sequence = Sequence(path)
                print(sequence)
                self.sequence_double_clicked.emit(sequence)  # type: ignore
