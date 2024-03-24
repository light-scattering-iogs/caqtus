# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'graphplot_main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.6.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QMainWindow, QMenu, QMenuBar,
    QSizePolicy, QStatusBar, QWidget)

class Ui_GraphPlotMainWindow(object):
    def setupUi(self, GraphPlotMainWindow):
        if not GraphPlotMainWindow.objectName():
            GraphPlotMainWindow.setObjectName(u"GraphPlotMainWindow")
        GraphPlotMainWindow.resize(800, 600)
        self.centralwidget = QWidget(GraphPlotMainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        GraphPlotMainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(GraphPlotMainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 800, 21))
        self.docks_menu = QMenu(self.menubar)
        self.docks_menu.setObjectName(u"docks_menu")
        GraphPlotMainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(GraphPlotMainWindow)
        self.statusbar.setObjectName(u"statusbar")
        GraphPlotMainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.docks_menu.menuAction())

        self.retranslateUi(GraphPlotMainWindow)

        QMetaObject.connectSlotsByName(GraphPlotMainWindow)
    # setupUi

    def retranslateUi(self, GraphPlotMainWindow):
        GraphPlotMainWindow.setWindowTitle(QCoreApplication.translate("GraphPlotMainWindow", u"MainWindow", None))
        self.docks_menu.setTitle(QCoreApplication.translate("GraphPlotMainWindow", u"Docks", None))
    # retranslateUi

