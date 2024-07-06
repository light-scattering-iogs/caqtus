# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'add_image_dialog.ui'
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


class Ui_ImageDialog(object):
    def setupUi(self, ImageDialog):
        if not ImageDialog.objectName():
            ImageDialog.setObjectName("ImageDialog")
        ImageDialog.resize(400, 300)
        self.verticalLayout = QVBoxLayout(ImageDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName("formLayout")
        self.titleLabel = QLabel(ImageDialog)
        self.titleLabel.setObjectName("titleLabel")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.titleLabel)

        self._window_title = QLineEdit(ImageDialog)
        self._window_title.setObjectName("_window_title")

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self._window_title)

        self.cameraLabel = QLabel(ImageDialog)
        self.cameraLabel.setObjectName("cameraLabel")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.cameraLabel)

        self._camera_line_edit = QLineEdit(ImageDialog)
        self._camera_line_edit.setObjectName("_camera_line_edit")

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self._camera_line_edit)

        self.pictureLabel = QLabel(ImageDialog)
        self.pictureLabel.setObjectName("pictureLabel")

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.pictureLabel)

        self._picture_line_edit = QLineEdit(ImageDialog)
        self._picture_line_edit.setObjectName("_picture_line_edit")

        self.formLayout.setWidget(2, QFormLayout.FieldRole, self._picture_line_edit)

        self.verticalLayout.addLayout(self.formLayout)

        self.buttonBox = QDialogButtonBox(ImageDialog)
        self.buttonBox.setObjectName("buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)

        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(ImageDialog)
        self.buttonBox.accepted.connect(ImageDialog.accept)
        self.buttonBox.rejected.connect(ImageDialog.reject)

        QMetaObject.connectSlotsByName(ImageDialog)

    # setupUi

    def retranslateUi(self, ImageDialog):
        ImageDialog.setWindowTitle(
            QCoreApplication.translate("ImageDialog", "Dialog", None)
        )
        self.titleLabel.setText(
            QCoreApplication.translate("ImageDialog", "Title", None)
        )
        self.cameraLabel.setText(
            QCoreApplication.translate("ImageDialog", "Camera", None)
        )
        self.pictureLabel.setText(
            QCoreApplication.translate("ImageDialog", "Picture", None)
        )

    # retranslateUi
