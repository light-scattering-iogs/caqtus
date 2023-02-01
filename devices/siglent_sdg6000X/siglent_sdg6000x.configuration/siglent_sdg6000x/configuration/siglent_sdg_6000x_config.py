from device_config import DeviceConfiguration


class SiglentSDG6000XConfiguration(DeviceConfiguration):
    def get_device_type(self) -> str:
        return "SiglentSDG6000XWaveformGenerator"
