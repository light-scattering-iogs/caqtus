# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'device_configurations_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.6.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QHBoxLayout, QSizePolicy, QToolButton, QVBoxLayout,
    QWidget)

class Ui_DeviceConfigurationsDialog(object):
    def setupUi(self, DeviceConfigurationsDialog):
        if not DeviceConfigurationsDialog.objectName():
            DeviceConfigurationsDialog.setObjectName(u"DeviceConfigurationsDialog")
        DeviceConfigurationsDialog.resize(620, 319)
        self.verticalLayout = QVBoxLayout(DeviceConfigurationsDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(6)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.add_device_button = QToolButton(DeviceConfigurationsDialog)
        self.add_device_button.setObjectName(u"add_device_button")

        self.horizontalLayout.addWidget(self.add_device_button)

        self.remove_device_button = QToolButton(DeviceConfigurationsDialog)
        self.remove_device_button.setObjectName(u"remove_device_button")

        self.horizontalLayout.addWidget(self.remove_device_button)

        self.buttonBox = QDialogButtonBox(DeviceConfigurationsDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Save)

        self.horizontalLayout.addWidget(self.buttonBox)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.retranslateUi(DeviceConfigurationsDialog)
        self.buttonBox.accepted.connect(DeviceConfigurationsDialog.accept)
        self.buttonBox.rejected.connect(DeviceConfigurationsDialog.reject)

        QMetaObject.connectSlotsByName(DeviceConfigurationsDialog)
    # setupUi

    def retranslateUi(self, DeviceConfigurationsDialog):
        DeviceConfigurationsDialog.setWindowTitle(QCoreApplication.translate("DeviceConfigurationsDialog", u"Edit device configurations...", None))
        self.add_device_button.setText(QCoreApplication.translate("DeviceConfigurationsDialog", u"...", None))
        self.remove_device_button.setText(QCoreApplication.translate("DeviceConfigurationsDialog", u"...", None))
    # retranslateUi

