from collections.abc import Sequence

from PyQt6.QtWidgets import QComboBox

from device_server.name import DeviceServerName


class RemoteServerComboBox(QComboBox):
    """A combo box to select a remote server"""

    def set_servers(self, servers: Sequence[DeviceServerName]):
        self.clear()
        self.addItems(servers)

    def set_current_server(self, server: DeviceServerName):
        self.setCurrentText(str(server))

    def get_current_server(self) -> DeviceServerName:
        return DeviceServerName(self.currentText())
