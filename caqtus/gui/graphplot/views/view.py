import abc

import polars
from PySide6.QtWidgets import QWidget

from caqtus.gui.qtutil.qabc import QABCMeta


class DataView(QWidget, metaclass=QABCMeta):
    @abc.abstractmethod
    async def update_data(self, data: polars.DataFrame) -> None:
        raise NotImplementedError
