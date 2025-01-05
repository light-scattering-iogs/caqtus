# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'device_configurations_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.8.0
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
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QSizePolicy,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class Ui_DeviceConfigurationsDialog(object):
    def setupUi(self, DeviceConfigurationsDialog):
        if not DeviceConfigurationsDialog.objectName():
            DeviceConfigurationsDialog.setObjectName("DeviceConfigurationsDialog")
        DeviceConfigurationsDialog.resize(775, 570)
        self.verticalLayout = QVBoxLayout(DeviceConfigurationsDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.splitter = QSplitter(DeviceConfigurationsDialog)
        self.splitter.setObjectName("splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.listView = QListView(self.splitter)
        self.listView.setObjectName("listView")
        self.splitter.addWidget(self.listView)
        self.device_widget = QWidget(self.splitter)
        self.device_widget.setObjectName("device_widget")
        self.verticalLayout_2 = QVBoxLayout(self.device_widget)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.form_layout = QFormLayout()
        self.form_layout.setObjectName("form_layout")
        self.deviceNameLabel = QLabel(self.device_widget)
        self.deviceNameLabel.setObjectName("deviceNameLabel")

        self.form_layout.setWidget(0, QFormLayout.LabelRole, self.deviceNameLabel)

        self.deviceNameLineEdit = QLineEdit(self.device_widget)
        self.deviceNameLineEdit.setObjectName("deviceNameLineEdit")

        self.form_layout.setWidget(0, QFormLayout.FieldRole, self.deviceNameLineEdit)

        self.verticalLayout_2.addLayout(self.form_layout)

        self.splitter.addWidget(self.device_widget)

        self.verticalLayout.addWidget(self.splitter)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(6)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.add_device_button = QToolButton(DeviceConfigurationsDialog)
        self.add_device_button.setObjectName("add_device_button")

        self.horizontalLayout.addWidget(self.add_device_button)

        self.remove_device_button = QToolButton(DeviceConfigurationsDialog)
        self.remove_device_button.setObjectName("remove_device_button")

        self.horizontalLayout.addWidget(self.remove_device_button)

        self.buttonBox = QDialogButtonBox(DeviceConfigurationsDialog)
        self.buttonBox.setObjectName("buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )

        self.horizontalLayout.addWidget(self.buttonBox)

        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(DeviceConfigurationsDialog)
        self.buttonBox.accepted.connect(DeviceConfigurationsDialog.accept)
        self.buttonBox.rejected.connect(DeviceConfigurationsDialog.reject)

        QMetaObject.connectSlotsByName(DeviceConfigurationsDialog)

    # setupUi

    def retranslateUi(self, DeviceConfigurationsDialog):
        DeviceConfigurationsDialog.setWindowTitle(
            QCoreApplication.translate(
                "DeviceConfigurationsDialog", "Edit device configurations...", None
            )
        )
        self.deviceNameLabel.setText(
            QCoreApplication.translate(
                "DeviceConfigurationsDialog", "Device name", None
            )
        )
        self.add_device_button.setText(
            QCoreApplication.translate("DeviceConfigurationsDialog", "...", None)
        )
        self.remove_device_button.setText(
            QCoreApplication.translate("DeviceConfigurationsDialog", "...", None)
        )

    # retranslateUi
