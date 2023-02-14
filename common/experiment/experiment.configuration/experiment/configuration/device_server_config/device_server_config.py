from pydantic import SecretStr

from settings_model import SettingsModel


class DeviceServerConfiguration(SettingsModel):
    address: str
    port: int
    authkey: SecretStr
