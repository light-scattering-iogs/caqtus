# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'add_constant_table.ui'
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

class Ui_AddTableDialog(object):
    def setupUi(self, AddTableDialog):
        if not AddTableDialog.objectName():
            AddTableDialog.setObjectName(u"AddTableDialog")
        AddTableDialog.resize(400, 69)
        self.verticalLayout = QVBoxLayout(AddTableDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.deviceNameLabel = QLabel(AddTableDialog)
        self.deviceNameLabel.setObjectName(u"deviceNameLabel")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.deviceNameLabel)

        self.table_name_line_edit = QLineEdit(AddTableDialog)
        self.table_name_line_edit.setObjectName(u"table_name_line_edit")

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.table_name_line_edit)


        self.verticalLayout.addLayout(self.formLayout)

        self.buttonBox = QDialogButtonBox(AddTableDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(AddTableDialog)
        self.buttonBox.accepted.connect(AddTableDialog.accept)
        self.buttonBox.rejected.connect(AddTableDialog.reject)

        QMetaObject.connectSlotsByName(AddTableDialog)
    # setupUi

    def retranslateUi(self, AddTableDialog):
        AddTableDialog.setWindowTitle(QCoreApplication.translate("AddTableDialog", u"Add constant table...", None))
        self.deviceNameLabel.setText(QCoreApplication.translate("AddTableDialog", u"Table name", None))
    # retranslateUi

