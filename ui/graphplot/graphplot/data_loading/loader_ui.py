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
from PySide6.QtWidgets import (QApplication, QListWidget, QListWidgetItem, QProgressBar,
    QSizePolicy, QToolBox, QVBoxLayout, QWidget)

class Ui_Loader(object):
    def setupUi(self, Loader):
        if not Loader.objectName():
            Loader.setObjectName(u"Loader")
        Loader.resize(400, 301)
        self.verticalLayout = QVBoxLayout(Loader)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tool_box = QToolBox(Loader)
        self.tool_box.setObjectName(u"tool_box")
        self.widget = QWidget()
        self.widget.setObjectName(u"widget")
        self.widget.setGeometry(QRect(0, 0, 382, 202))
        self.verticalLayout_2 = QVBoxLayout(self.widget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.sequence_list = QListWidget(self.widget)
        self.sequence_list.setObjectName(u"sequence_list")

        self.verticalLayout_2.addWidget(self.sequence_list)

        self.tool_box.addItem(self.widget, u"Sequences")
        self.page_2 = QWidget()
        self.page_2.setObjectName(u"page_2")
        self.page_2.setGeometry(QRect(0, 0, 382, 202))
        self.tool_box.addItem(self.page_2, u"Loader")

        self.verticalLayout.addWidget(self.tool_box)

        self.progress_bar = QProgressBar(Loader)
        self.progress_bar.setObjectName(u"progress_bar")
        self.progress_bar.setValue(24)

        self.verticalLayout.addWidget(self.progress_bar)


        self.retranslateUi(Loader)

        self.tool_box.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(Loader)
    # setupUi

    def retranslateUi(self, Loader):
        Loader.setWindowTitle(QCoreApplication.translate("Loader", u"Form", None))
        self.tool_box.setItemText(self.tool_box.indexOf(self.widget), QCoreApplication.translate("Loader", u"Sequences", None))
        self.tool_box.setItemText(self.tool_box.indexOf(self.page_2), QCoreApplication.translate("Loader", u"Loader", None))
    # retranslateUi

