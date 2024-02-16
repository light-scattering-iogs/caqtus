# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'parameter_tables_editor.ui'
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
from PySide6.QtWidgets import (QApplication, QColumnView, QHBoxLayout, QPushButton,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget)

class Ui_ParameterTablesEditor(object):
    def setupUi(self, ParameterTablesEditor):
        if not ParameterTablesEditor.objectName():
            ParameterTablesEditor.setObjectName(u"ParameterTablesEditor")
        ParameterTablesEditor.resize(400, 300)
        self.verticalLayout = QVBoxLayout(ParameterTablesEditor)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.pushButton_3 = QPushButton(ParameterTablesEditor)
        self.pushButton_3.setObjectName(u"pushButton_3")

        self.horizontalLayout.addWidget(self.pushButton_3)

        self.pushButton_4 = QPushButton(ParameterTablesEditor)
        self.pushButton_4.setObjectName(u"pushButton_4")

        self.horizontalLayout.addWidget(self.pushButton_4)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.columnView = QColumnView(ParameterTablesEditor)
        self.columnView.setObjectName(u"columnView")

        self.verticalLayout.addWidget(self.columnView)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.add_button = QPushButton(ParameterTablesEditor)
        self.add_button.setObjectName(u"add_button")

        self.horizontalLayout_2.addWidget(self.add_button)

        self.delete_button = QPushButton(ParameterTablesEditor)
        self.delete_button.setObjectName(u"delete_button")

        self.horizontalLayout_2.addWidget(self.delete_button)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_2)


        self.verticalLayout.addLayout(self.horizontalLayout_2)


        self.retranslateUi(ParameterTablesEditor)

        QMetaObject.connectSlotsByName(ParameterTablesEditor)
    # setupUi

    def retranslateUi(self, ParameterTablesEditor):
        ParameterTablesEditor.setWindowTitle(QCoreApplication.translate("ParameterTablesEditor", u"Form", None))
        self.pushButton_3.setText(QCoreApplication.translate("ParameterTablesEditor", u"Write to default", None))
        self.pushButton_4.setText(QCoreApplication.translate("ParameterTablesEditor", u"Read from default", None))
        self.add_button.setText("")
        self.delete_button.setText("")
    # retranslateUi

