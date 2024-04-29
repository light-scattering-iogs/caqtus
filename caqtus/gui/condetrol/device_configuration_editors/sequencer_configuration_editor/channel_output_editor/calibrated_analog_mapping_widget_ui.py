# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'calibrated_analog_mapping_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QFormLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QSizePolicy, QSpacerItem,
    QTableView, QToolButton, QVBoxLayout, QWidget)

class Ui_CalibratedAnalogMappingWigdet(object):
    def setupUi(self, CalibratedAnalogMappingWigdet):
        if not CalibratedAnalogMappingWigdet.objectName():
            CalibratedAnalogMappingWigdet.setObjectName(u"CalibratedAnalogMappingWigdet")
        CalibratedAnalogMappingWigdet.resize(569, 376)
        self.horizontalLayout_2 = QHBoxLayout(CalibratedAnalogMappingWigdet)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.inputUnitLabel = QLabel(CalibratedAnalogMappingWigdet)
        self.inputUnitLabel.setObjectName(u"inputUnitLabel")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.inputUnitLabel)

        self.inputUnitLineEdit = QLineEdit(CalibratedAnalogMappingWigdet)
        self.inputUnitLineEdit.setObjectName(u"inputUnitLineEdit")

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.inputUnitLineEdit)

        self.outputUnitLabel = QLabel(CalibratedAnalogMappingWigdet)
        self.outputUnitLabel.setObjectName(u"outputUnitLabel")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.outputUnitLabel)

        self.outputUnitLineEdit = QLineEdit(CalibratedAnalogMappingWigdet)
        self.outputUnitLineEdit.setObjectName(u"outputUnitLineEdit")

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.outputUnitLineEdit)


        self.verticalLayout.addLayout(self.formLayout)

        self.tableView = QTableView(CalibratedAnalogMappingWigdet)
        self.tableView.setObjectName(u"tableView")
        self.tableView.horizontalHeader().setStretchLastSection(True)
        self.tableView.verticalHeader().setVisible(False)

        self.verticalLayout.addWidget(self.tableView)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.add_button = QToolButton(CalibratedAnalogMappingWigdet)
        self.add_button.setObjectName(u"add_button")

        self.horizontalLayout.addWidget(self.add_button)

        self.remove_button = QToolButton(CalibratedAnalogMappingWigdet)
        self.remove_button.setObjectName(u"remove_button")

        self.horizontalLayout.addWidget(self.remove_button)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.horizontalLayout_2.addLayout(self.verticalLayout)


        self.retranslateUi(CalibratedAnalogMappingWigdet)

        QMetaObject.connectSlotsByName(CalibratedAnalogMappingWigdet)
    # setupUi

    def retranslateUi(self, CalibratedAnalogMappingWigdet):
        CalibratedAnalogMappingWigdet.setWindowTitle(QCoreApplication.translate("CalibratedAnalogMappingWigdet", u"Form", None))
        self.inputUnitLabel.setText(QCoreApplication.translate("CalibratedAnalogMappingWigdet", u"Input unit", None))
        self.inputUnitLineEdit.setPlaceholderText(QCoreApplication.translate("CalibratedAnalogMappingWigdet", u"None", None))
        self.outputUnitLabel.setText(QCoreApplication.translate("CalibratedAnalogMappingWigdet", u"Output unit", None))
        self.outputUnitLineEdit.setPlaceholderText(QCoreApplication.translate("CalibratedAnalogMappingWigdet", u"None", None))
        self.add_button.setText(QCoreApplication.translate("CalibratedAnalogMappingWigdet", u"...", None))
        self.remove_button.setText(QCoreApplication.translate("CalibratedAnalogMappingWigdet", u"...", None))
    # retranslateUi

