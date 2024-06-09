# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'calibrated_analog_mapping_widget.ui'
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
    QApplication,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QSpacerItem,
    QTabWidget,
    QTableView,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class Ui_CalibratedAnalogMappingWigdet(object):
    def setupUi(self, CalibratedAnalogMappingWigdet):
        if not CalibratedAnalogMappingWigdet.objectName():
            CalibratedAnalogMappingWigdet.setObjectName("CalibratedAnalogMappingWigdet")
        CalibratedAnalogMappingWigdet.resize(758, 466)
        self.horizontalLayout_2 = QHBoxLayout(CalibratedAnalogMappingWigdet)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.tabWidget = QTabWidget(CalibratedAnalogMappingWigdet)
        self.tabWidget.setObjectName("tabWidget")
        self.curve_tab = QWidget()
        self.curve_tab.setObjectName("curve_tab")
        self.verticalLayout_2 = QVBoxLayout(self.curve_tab)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.tabWidget.addTab(self.curve_tab, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName("tab_2")
        self.verticalLayout_3 = QVBoxLayout(self.tab_2)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName("formLayout")
        self.inputUnitLabel = QLabel(self.tab_2)
        self.inputUnitLabel.setObjectName("inputUnitLabel")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.inputUnitLabel)

        self.inputUnitLineEdit = QLineEdit(self.tab_2)
        self.inputUnitLineEdit.setObjectName("inputUnitLineEdit")

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.inputUnitLineEdit)

        self.outputUnitLabel = QLabel(self.tab_2)
        self.outputUnitLabel.setObjectName("outputUnitLabel")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.outputUnitLabel)

        self.outputUnitLineEdit = QLineEdit(self.tab_2)
        self.outputUnitLineEdit.setObjectName("outputUnitLineEdit")

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.outputUnitLineEdit)

        self.verticalLayout.addLayout(self.formLayout)

        self.tableView = QTableView(self.tab_2)
        self.tableView.setObjectName("tableView")
        self.tableView.horizontalHeader().setStretchLastSection(True)
        self.tableView.verticalHeader().setVisible(False)

        self.verticalLayout.addWidget(self.tableView)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.add_button = QToolButton(self.tab_2)
        self.add_button.setObjectName("add_button")

        self.horizontalLayout.addWidget(self.add_button)

        self.remove_button = QToolButton(self.tab_2)
        self.remove_button.setObjectName("remove_button")

        self.horizontalLayout.addWidget(self.remove_button)

        self.horizontalSpacer = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.verticalLayout.addLayout(self.horizontalLayout)

        self.verticalLayout_3.addLayout(self.verticalLayout)

        self.tabWidget.addTab(self.tab_2, "")

        self.horizontalLayout_2.addWidget(self.tabWidget)

        self.retranslateUi(CalibratedAnalogMappingWigdet)

        self.tabWidget.setCurrentIndex(0)

        QMetaObject.connectSlotsByName(CalibratedAnalogMappingWigdet)

    # setupUi

    def retranslateUi(self, CalibratedAnalogMappingWigdet):
        CalibratedAnalogMappingWigdet.setWindowTitle(
            QCoreApplication.translate("CalibratedAnalogMappingWigdet", "Form", None)
        )
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.curve_tab),
            QCoreApplication.translate("CalibratedAnalogMappingWigdet", "Curve", None),
        )
        self.inputUnitLabel.setText(
            QCoreApplication.translate(
                "CalibratedAnalogMappingWigdet", "Input unit", None
            )
        )
        self.inputUnitLineEdit.setPlaceholderText(
            QCoreApplication.translate("CalibratedAnalogMappingWigdet", "None", None)
        )
        self.outputUnitLabel.setText(
            QCoreApplication.translate(
                "CalibratedAnalogMappingWigdet", "Output unit", None
            )
        )
        self.outputUnitLineEdit.setPlaceholderText(
            QCoreApplication.translate("CalibratedAnalogMappingWigdet", "None", None)
        )
        self.add_button.setText(
            QCoreApplication.translate("CalibratedAnalogMappingWigdet", "...", None)
        )
        self.remove_button.setText(
            QCoreApplication.translate("CalibratedAnalogMappingWigdet", "...", None)
        )
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.tab_2),
            QCoreApplication.translate("CalibratedAnalogMappingWigdet", "Values", None),
        )

    # retranslateUi
