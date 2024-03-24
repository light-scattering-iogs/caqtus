from PySide6.QtWidgets import QSpinBox

from caqtus.gui.condetrol.device_configuration_editors.camera_configuration_editor.editor import (
    CameraConfigurationEditor,
)
from caqtus.utils.roi import RectangularROI, Width, Height
from ..configuration import OrcaQuestCameraConfiguration


class OrcaQuestConfigurationEditor(
    CameraConfigurationEditor[OrcaQuestCameraConfiguration]
):
    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self._camera_number_spinbox = QSpinBox()
        self._camera_number_spinbox.setRange(0, 100)
        self.form.insertRow(0, "Camera number", self._camera_number_spinbox)
        self.update_ui_from_config(self.device_config)

    def update_config_from_ui(
        self, device_config: OrcaQuestCameraConfiguration
    ) -> OrcaQuestCameraConfiguration:
        device_config = super().update_config_from_ui(device_config)
        device_config.camera_number = self._camera_number_spinbox.value()
        return device_config

    def update_ui_from_config(
        self, device_config: OrcaQuestCameraConfiguration
    ) -> None:
        super().update_ui_from_config(device_config)
        self._camera_number_spinbox.setValue(device_config.camera_number)

    @classmethod
    def get_default_configuration(cls) -> OrcaQuestCameraConfiguration:
        return OrcaQuestCameraConfiguration(
            camera_number=0,
            remote_server="default",
            roi=RectangularROI(
                original_image_size=(Width(4096), Height(2304)),
                x=0,
                y=0,
                width=4096,
                height=2304,
            ),
        )
