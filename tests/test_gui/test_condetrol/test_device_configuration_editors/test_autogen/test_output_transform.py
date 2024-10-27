from caqtus.device import DeviceConfiguration
from caqtus.device.output_transform import EvaluableOutput


class DeviceWithOutputTransform(DeviceConfiguration):
    output: EvaluableOutput
