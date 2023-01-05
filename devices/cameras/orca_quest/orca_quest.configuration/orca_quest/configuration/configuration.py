from camera.configuration import CameraConfiguration


class OrcaQuestCameraConfiguration(CameraConfiguration):
    camera_number: int

    @classmethod
    def get_device_type(cls) -> str:
        return "OrcaQuestCamera"

    def get_device_init_args(self) -> dict[str]:
        extra = {
            "camera_number": self.camera_number,
        }
        return super().get_device_init_args() | extra
