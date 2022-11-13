from settings_model import SettingsModel


class DeviceServerConfiguration(SettingsModel):
    address: str
    port: int