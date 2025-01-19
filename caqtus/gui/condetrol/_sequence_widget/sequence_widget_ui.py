# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'sequence_widget.ui'
##
## Created by: Qt User Interface Compiler version 6.8.0
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
from PySide6.QtWidgets import (QApplication, QSizePolicy, QSplitter, QTabWidget,
    QUndoView, QVBoxLayout, QWidget)

class Ui_SequenceWidget(object):
    def setupUi(self, SequenceWidget):
        if not SequenceWidget.objectName():
            SequenceWidget.setObjectName(u"SequenceWidget")
        SequenceWidget.resize(742, 412)
        self.verticalLayout = QVBoxLayout(SequenceWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.splitter = QSplitter(SequenceWidget)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.tabWidget = QTabWidget(self.splitter)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setTabPosition(QTabWidget.TabPosition.North)
        self.Constants = QWidget()
        self.Constants.setObjectName(u"Constants")
        self.tabWidget.addTab(self.Constants, "")
        self.iteration_tab = QWidget()
        self.iteration_tab.setObjectName(u"iteration_tab")
        self.tabWidget.addTab(self.iteration_tab, "")
        self.Timelanes = QWidget()
        self.Timelanes.setObjectName(u"Timelanes")
        self.tabWidget.addTab(self.Timelanes, "")
        self.splitter.addWidget(self.tabWidget)
        self.undoView = QUndoView(self.splitter)
        self.undoView.setObjectName(u"undoView")
        self.splitter.addWidget(self.undoView)

        self.verticalLayout.addWidget(self.splitter)


        self.retranslateUi(SequenceWidget)

        self.tabWidget.setCurrentIndex(2)


        QMetaObject.connectSlotsByName(SequenceWidget)
    # setupUi

    def retranslateUi(self, SequenceWidget):
        SequenceWidget.setWindowTitle(QCoreApplication.translate("SequenceWidget", u"Form", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.Constants), QCoreApplication.translate("SequenceWidget", u"Constants", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.iteration_tab), QCoreApplication.translate("SequenceWidget", u"Iteration", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.Timelanes), QCoreApplication.translate("SequenceWidget", u"Shot", None))
    # retranslateUi

