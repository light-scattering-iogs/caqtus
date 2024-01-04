from PyQt6.QtWidgets import QListView

from core.session import ConstantTable


class ConstantTableEditor(QListView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.table: ConstantTable = []

    def set_table(self, table: ConstantTable):
        self.table = table

    def get_table(self) -> ConstantTable:
        return self.table
