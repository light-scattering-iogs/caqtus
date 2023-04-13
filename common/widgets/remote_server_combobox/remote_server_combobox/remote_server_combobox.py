from PyQt6.QtWidgets import QComboBox


class RemoteServerComboBox(QComboBox):
    """A combo box to select a remote server"""

    def set_servers(self, servers: list[str]):
        self.clear()
        self.addItems(servers)

    def set_current_server(self, server: str):
        self.setCurrentText(server)

    def get_current_server(self) -> str:
        return self.currentText()
