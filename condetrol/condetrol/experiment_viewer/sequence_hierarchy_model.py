from typing import Optional

from PyQt6.QtCore import QAbstractItemModel
from sqlalchemy.orm import sessionmaker
from sequence.runtime import SequencePath


class SequenceHierarchyModel(QAbstractItemModel):
    """Tree model for sequence hierarchy.

    This model stores an in-memory representation of the database sequence structure.
    """

    def __init__(self, session_maker: sessionmaker):
        super().__init__()
        self._session_maker = session_maker
        self._level: Optional[SequencePath] = None

    def set_working_level(self, level: Optional[SequencePath]):
        self.beginResetModel()
        self._level = level

        self.endResetModel()
        
    @property
    def _session(self):
        return self._session_maker.begin()

