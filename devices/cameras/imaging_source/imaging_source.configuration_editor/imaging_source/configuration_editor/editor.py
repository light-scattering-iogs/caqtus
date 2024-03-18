from PySide6.QtWidgets import QLineEdit

from condetrol.device_configuration_editors.camera_configuration_editor.editor import (
    CameraConfigurationEditor,
)
from imaging_source.configuration import ImagingSourceCameraConfiguration
from util.roi import RectangularROI, Width, Height


class OrcaQuestConfigurationEditor(
    CameraConfigurationEditor[ImagingSourceCameraConfiguration]
):
    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self._camera_name = QLineEdit()
        self.form.insertRow(0, "Camera name", self._camera_name)
        self.update_ui_from_config(self.device_config)

    def update_config_from_ui(
        self, device_config: ImagingSourceCameraConfiguration
    ) -> ImagingSourceCameraConfiguration:
        device_config = super().update_config_from_ui(device_config)
        device_config.camera_name = self._camera_name.text()
        return device_config

    def update_ui_from_config(
        self, device_config: ImagingSourceCameraConfiguration
    ) -> None:
        super().update_ui_from_config(device_config)
        self._camera_name.setText(device_config.camera_name)

    @classmethod
    def get_default_configuration(cls) -> ImagingSourceCameraConfiguration:
        return ImagingSourceCameraConfiguration(
            camera_name="",
            remote_server="default",
            format="Y800",
            roi=RectangularROI(
                original_image_size=(Width(1280), Height(960)),
                x=0,
                y=0,
                width=1280,
                height=960,
            ),
        )
