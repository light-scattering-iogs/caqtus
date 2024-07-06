# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'image_view_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
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
    QLabel,
    QLineEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class Ui_ImageViewDialog(object):
    def setupUi(self, ImageViewDialog):
        if not ImageViewDialog.objectName():
            ImageViewDialog.setObjectName("ImageViewDialog")
        ImageViewDialog.resize(400, 300)
        ImageViewDialog.setModal(True)
        self.verticalLayout = QVBoxLayout(ImageViewDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName("formLayout")
        self.viewNameLabel = QLabel(ImageViewDialog)
        self.viewNameLabel.setObjectName("viewNameLabel")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.viewNameLabel)

        self.view_name_line_edit = QLineEdit(ImageViewDialog)
        self.view_name_line_edit.setObjectName("view_name_line_edit")

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.view_name_line_edit)

        self.cameraNameLabel = QLabel(ImageViewDialog)
        self.cameraNameLabel.setObjectName("cameraNameLabel")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.cameraNameLabel)

        self.camera_name_line_edit = QLineEdit(ImageViewDialog)
        self.camera_name_line_edit.setObjectName("camera_name_line_edit")

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.camera_name_line_edit)

        self.imageLabel = QLabel(ImageViewDialog)
        self.imageLabel.setObjectName("imageLabel")

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.imageLabel)

        self.image_line_edit = QLineEdit(ImageViewDialog)
        self.image_line_edit.setObjectName("image_line_edit")

        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.image_line_edit)

        self.backgroundLabel = QLabel(ImageViewDialog)
        self.backgroundLabel.setObjectName("backgroundLabel")

        self.formLayout.setWidget(3, QFormLayout.LabelRole, self.backgroundLabel)

        self.background_line_edit = QLineEdit(ImageViewDialog)
        self.background_line_edit.setObjectName("background_line_edit")

        self.formLayout.setWidget(3, QFormLayout.FieldRole, self.background_line_edit)

        self.verticalLayout.addLayout(self.formLayout)

        self.buttonBox = QDialogButtonBox(ImageViewDialog)
        self.buttonBox.setObjectName("buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)

        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(ImageViewDialog)
        self.buttonBox.accepted.connect(ImageViewDialog.accept)
        self.buttonBox.rejected.connect(ImageViewDialog.reject)

        QMetaObject.connectSlotsByName(ImageViewDialog)

    # setupUi

    def retranslateUi(self, ImageViewDialog):
        ImageViewDialog.setWindowTitle(
            QCoreApplication.translate("ImageViewDialog", "Create image view...", None)
        )
        self.viewNameLabel.setText(
            QCoreApplication.translate("ImageViewDialog", "View name", None)
        )
        self.cameraNameLabel.setText(
            QCoreApplication.translate("ImageViewDialog", "Camera", None)
        )
        self.imageLabel.setText(
            QCoreApplication.translate("ImageViewDialog", "Image", None)
        )
        self.backgroundLabel.setText(
            QCoreApplication.translate("ImageViewDialog", "Background", None)
        )
        self.background_line_edit.setPlaceholderText(
            QCoreApplication.translate("ImageViewDialog", "None", None)
        )

    # retranslateUi
