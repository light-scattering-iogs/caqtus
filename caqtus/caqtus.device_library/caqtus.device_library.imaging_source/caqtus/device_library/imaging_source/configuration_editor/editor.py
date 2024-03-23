from PySide6.QtWidgets import QLineEdit, QComboBox
from caqtus.utils.roi import RectangularROI, Width, Height

from caqtus.gui.condetrol.device_configuration_editors.camera_configuration_editor.editor import (
    CameraConfigurationEditor,
)
from ..configuration import ImagingSourceCameraConfiguration


class ImagingSourceCameraConfigurationEditor(
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
        self._format_combo_box = QComboBox()
        self._format_combo_box.addItems(["Y800", "Y16"])
        self.form.insertRow(1, "Format", self._format_combo_box)
        self.update_ui_from_config(self.device_config)

    def update_config_from_ui(
        self, device_config: ImagingSourceCameraConfiguration
    ) -> ImagingSourceCameraConfiguration:
        device_config = super().update_config_from_ui(device_config)
        device_config.camera_name = self._camera_name.text()
        device_config.format = self._format_combo_box.currentText()
        return device_config

    def update_ui_from_config(
        self, device_config: ImagingSourceCameraConfiguration
    ) -> None:
        super().update_ui_from_config(device_config)
        self._camera_name.setText(device_config.camera_name)
        self._format_combo_box.setCurrentText(device_config.format)

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
