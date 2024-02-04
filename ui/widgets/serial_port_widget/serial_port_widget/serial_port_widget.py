from PySide6.QtWidgets import QLineEdit


class SerialPortWidget(QLineEdit):
    """A widget to select a serial port"""

    def set_port(self, port: str):
        self.setText(port)

    def get_port(self) -> str:
        return self.text()
