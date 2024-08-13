# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'add_device_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.6.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (
    QCoreApplication,
    QDate,
    QDateTime,
    QLocale,
    QMetaObject,
    QObject,
    QPoint,
    QRect,
    QSize,
    QTime,
    QUrl,
    Qt,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QCursor,
    QFont,
    QFontDatabase,
    QGradient,
    QIcon,
    QImage,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPalette,
    QPixmap,
    QRadialGradient,
    QTransform,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class Ui_AddDeviceDialog(object):
    def setupUi(self, AddDeviceDialog):
        if not AddDeviceDialog.objectName():
            AddDeviceDialog.setObjectName("AddDeviceDialog")
        AddDeviceDialog.resize(400, 300)
        self.verticalLayout = QVBoxLayout(AddDeviceDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName("formLayout")
        self.deviceNameLabel = QLabel(AddDeviceDialog)
        self.deviceNameLabel.setObjectName("deviceNameLabel")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.deviceNameLabel)

        self.device_name_line_edit = QLineEdit(AddDeviceDialog)
        self.device_name_line_edit.setObjectName("device_name_line_edit")

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.device_name_line_edit)

        self.deviceTypeLabel = QLabel(AddDeviceDialog)
        self.deviceTypeLabel.setObjectName("deviceTypeLabel")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.deviceTypeLabel)

        self.device_type_combo_box = QComboBox(AddDeviceDialog)
        self.device_type_combo_box.setObjectName("device_type_combo_box")

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.device_type_combo_box)

        self.verticalLayout.addLayout(self.formLayout)

        self.buttonBox = QDialogButtonBox(AddDeviceDialog)
        self.buttonBox.setObjectName("buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)

        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(AddDeviceDialog)
        self.buttonBox.accepted.connect(AddDeviceDialog.accept)
        self.buttonBox.rejected.connect(AddDeviceDialog.reject)

        QMetaObject.connectSlotsByName(AddDeviceDialog)

    # setupUi

    def retranslateUi(self, AddDeviceDialog):
        AddDeviceDialog.setWindowTitle(
            QCoreApplication.translate("AddDeviceDialog", "Add device...", None)
        )
        self.deviceNameLabel.setText(
            QCoreApplication.translate("AddDeviceDialog", "Device name", None)
        )
        self.deviceTypeLabel.setText(
            QCoreApplication.translate("AddDeviceDialog", "Device type", None)
        )

    # retranslateUi
