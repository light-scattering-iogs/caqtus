# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'create_parameters_viewer.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
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
    QFormLayout, QLabel, QLineEdit, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_ParametersDialog(object):
    def setupUi(self, ParametersDialog):
        if not ParametersDialog.objectName():
            ParametersDialog.setObjectName(u"ParametersDialog")
        ParametersDialog.resize(400, 300)
        self.verticalLayout = QVBoxLayout(ParametersDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.titleLabel = QLabel(ParametersDialog)
        self.titleLabel.setObjectName(u"titleLabel")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.titleLabel)

        self._window_title = QLineEdit(ParametersDialog)
        self._window_title.setObjectName(u"_window_title")

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self._window_title)


        self.verticalLayout.addLayout(self.formLayout)

        self.buttonBox = QDialogButtonBox(ParametersDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(ParametersDialog)
        self.buttonBox.accepted.connect(ParametersDialog.accept)
        self.buttonBox.rejected.connect(ParametersDialog.reject)

        QMetaObject.connectSlotsByName(ParametersDialog)
    # setupUi

    def retranslateUi(self, ParametersDialog):
        ParametersDialog.setWindowTitle(QCoreApplication.translate("ParametersDialog", u"Dialog", None))
        self.titleLabel.setText(QCoreApplication.translate("ParametersDialog", u"Title", None))
    # retranslateUi

