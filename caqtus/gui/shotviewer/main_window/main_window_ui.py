# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.6.3
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

class Ui_ShotViewerMainWindow(object):
    def setupUi(self, ShotViewerMainWindow):
        if not ShotViewerMainWindow.objectName():
            ShotViewerMainWindow.setObjectName(u"ShotViewerMainWindow")
        ShotViewerMainWindow.resize(800, 515)
        self.action_save_workspace_as = QAction(ShotViewerMainWindow)
        self.action_save_workspace_as.setObjectName(u"action_save_workspace_as")
        self.action_load_workspace = QAction(ShotViewerMainWindow)
        self.action_load_workspace.setObjectName(u"action_load_workspace")
        self.tile_action = QAction(ShotViewerMainWindow)
        self.tile_action.setObjectName(u"tile_action")
        self.centralwidget = QWidget(ShotViewerMainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        ShotViewerMainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(ShotViewerMainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 800, 21))
        self.menu_add_view = QMenu(self.menubar)
        self.menu_add_view.setObjectName(u"menu_add_view")
        self.menuWorkspace = QMenu(self.menubar)
        self.menuWorkspace.setObjectName(u"menuWorkspace")
        self.menuWindows = QMenu(self.menubar)
        self.menuWindows.setObjectName(u"menuWindows")
        ShotViewerMainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(ShotViewerMainWindow)
        self.statusbar.setObjectName(u"statusbar")
        ShotViewerMainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menu_add_view.menuAction())
        self.menubar.addAction(self.menuWorkspace.menuAction())
        self.menubar.addAction(self.menuWindows.menuAction())
        self.menuWorkspace.addAction(self.action_save_workspace_as)
        self.menuWorkspace.addAction(self.action_load_workspace)
        self.menuWindows.addAction(self.tile_action)

        self.retranslateUi(ShotViewerMainWindow)

        QMetaObject.connectSlotsByName(ShotViewerMainWindow)
    # setupUi

    def retranslateUi(self, ShotViewerMainWindow):
        ShotViewerMainWindow.setWindowTitle(QCoreApplication.translate("ShotViewerMainWindow", u"MainWindow", None))
        self.action_save_workspace_as.setText(QCoreApplication.translate("ShotViewerMainWindow", u"Save as...", None))
        self.action_load_workspace.setText(QCoreApplication.translate("ShotViewerMainWindow", u"Load...", None))
        self.tile_action.setText(QCoreApplication.translate("ShotViewerMainWindow", u"Tile", None))
        self.menu_add_view.setTitle(QCoreApplication.translate("ShotViewerMainWindow", u"Add view", None))
        self.menuWorkspace.setTitle(QCoreApplication.translate("ShotViewerMainWindow", u"Workspace", None))
        self.menuWindows.setTitle(QCoreApplication.translate("ShotViewerMainWindow", u"Windows", None))
    # retranslateUi

