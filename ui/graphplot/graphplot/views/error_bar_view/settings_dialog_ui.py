# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'settings_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.6.2
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
from PySide6.QtWidgets import (QApplication, QDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_SettingsDialog(object):
    def setupUi(self, SettingsDialog):
        if not SettingsDialog.objectName():
            SettingsDialog.setObjectName(u"SettingsDialog")
        SettingsDialog.resize(400, 300)
        self.verticalLayout = QVBoxLayout(SettingsDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.xAxisLabel = QLabel(SettingsDialog)
        self.xAxisLabel.setObjectName(u"xAxisLabel")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.xAxisLabel)

        self.x_line_edit = QLineEdit(SettingsDialog)
        self.x_line_edit.setObjectName(u"x_line_edit")

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.x_line_edit)

        self.yAxisLabel = QLabel(SettingsDialog)
        self.yAxisLabel.setObjectName(u"yAxisLabel")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.yAxisLabel)

        self.y_line_edit = QLineEdit(SettingsDialog)
        self.y_line_edit.setObjectName(u"y_line_edit")

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.y_line_edit)

        self.hueLabel = QLabel(SettingsDialog)
        self.hueLabel.setObjectName(u"hueLabel")

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.hueLabel)

        self.hue_line_edit = QLineEdit(SettingsDialog)
        self.hue_line_edit.setObjectName(u"hue_line_edit")

        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.hue_line_edit)


        self.verticalLayout.addLayout(self.formLayout)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.ok_button = QPushButton(SettingsDialog)
        self.ok_button.setObjectName(u"ok_button")

        self.horizontalLayout.addWidget(self.ok_button)

        self.horizontalLayout.setStretch(0, 1)

        self.verticalLayout.addLayout(self.horizontalLayout)


        self.retranslateUi(SettingsDialog)

        QMetaObject.connectSlotsByName(SettingsDialog)
    # setupUi

    def retranslateUi(self, SettingsDialog):
        SettingsDialog.setWindowTitle(QCoreApplication.translate("SettingsDialog", u"Dialog", None))
        self.xAxisLabel.setText(QCoreApplication.translate("SettingsDialog", u"x axis", None))
        self.yAxisLabel.setText(QCoreApplication.translate("SettingsDialog", u"y axis", None))
        self.hueLabel.setText(QCoreApplication.translate("SettingsDialog", u"hue", None))
        self.hue_line_edit.setPlaceholderText(QCoreApplication.translate("SettingsDialog", u"None", None))
        self.ok_button.setText(QCoreApplication.translate("SettingsDialog", u"Ok", None))
    # retranslateUi

