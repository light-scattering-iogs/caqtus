# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'loader.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

class Ui_Loader(object):
    def setupUi(self, Loader):
        if not Loader.objectName():
            Loader.setObjectName(u"Loader")
        Loader.resize(645, 481)
        self.verticalLayout = QVBoxLayout(Loader)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.sequence_list = QListWidget(Loader)
        self.sequence_list.setObjectName(u"sequence_list")

        self.verticalLayout.addWidget(self.sequence_list)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.clear_button = QPushButton(Loader)
        self.clear_button.setObjectName(u"clear_button")

        self.horizontalLayout.addWidget(self.clear_button)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.retranslateUi(Loader)

        QMetaObject.connectSlotsByName(Loader)
    # setupUi

    def retranslateUi(self, Loader):
        Loader.setWindowTitle(QCoreApplication.translate("Loader", u"Form", None))
        self.clear_button.setText(QCoreApplication.translate("Loader", u"Clear", None))
    # retranslateUi

