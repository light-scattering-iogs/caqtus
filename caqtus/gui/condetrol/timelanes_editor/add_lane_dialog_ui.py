# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'add_lane_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QDialog,
    QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_AddLaneDialog(object):
    def setupUi(self, AddLaneDialog):
        if not AddLaneDialog.objectName():
            AddLaneDialog.setObjectName(u"AddLaneDialog")
        AddLaneDialog.resize(400, 300)
        self.verticalLayout = QVBoxLayout(AddLaneDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.lane_name_label = QLabel(AddLaneDialog)
        self.lane_name_label.setObjectName(u"lane_name_label")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.lane_name_label)

        self.lane_name_line_edit = QLineEdit(AddLaneDialog)
        self.lane_name_line_edit.setObjectName(u"lane_name_line_edit")

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.lane_name_line_edit)

        self.laneTypeLabel = QLabel(AddLaneDialog)
        self.laneTypeLabel.setObjectName(u"laneTypeLabel")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.laneTypeLabel)

        self.lane_type_combobox = QComboBox(AddLaneDialog)
        self.lane_type_combobox.setObjectName(u"lane_type_combobox")

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.lane_type_combobox)


        self.verticalLayout.addLayout(self.formLayout)

        self.buttonBox = QDialogButtonBox(AddLaneDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(AddLaneDialog)
        self.buttonBox.accepted.connect(AddLaneDialog.accept)
        self.buttonBox.rejected.connect(AddLaneDialog.reject)

        QMetaObject.connectSlotsByName(AddLaneDialog)
    # setupUi

    def retranslateUi(self, AddLaneDialog):
        AddLaneDialog.setWindowTitle(QCoreApplication.translate("AddLaneDialog", u"Dialog", None))
        self.lane_name_label.setText(QCoreApplication.translate("AddLaneDialog", u"Lane name", None))
        self.lane_name_line_edit.setPlaceholderText(QCoreApplication.translate("AddLaneDialog", u"Name", None))
        self.laneTypeLabel.setText(QCoreApplication.translate("AddLaneDialog", u"Lane type", None))
    # retranslateUi

