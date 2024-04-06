from caqtus.device import Device


class MockDevice(Device):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def get_name(self):
        return self.name
