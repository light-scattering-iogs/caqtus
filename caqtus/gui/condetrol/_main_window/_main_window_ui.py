# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.7.2
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
    QAction,
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
    QMainWindow,
    QMenu,
    QMenuBar,
    QSizePolicy,
    QWidget,
)


class Ui_CondetrolMainWindow(object):
    def setupUi(self, CondetrolMainWindow):
        if not CondetrolMainWindow.objectName():
            CondetrolMainWindow.setObjectName("CondetrolMainWindow")
        CondetrolMainWindow.resize(800, 600)
        self.action_edit_device_configurations = QAction(CondetrolMainWindow)
        self.action_edit_device_configurations.setObjectName(
            "action_edit_device_configurations"
        )
        self.actionExport = QAction(CondetrolMainWindow)
        self.actionExport.setObjectName("actionExport")
        self.actionLoad = QAction(CondetrolMainWindow)
        self.actionLoad.setObjectName("actionLoad")
        self.action_edit_constants = QAction(CondetrolMainWindow)
        self.action_edit_constants.setObjectName("action_edit_constants")
        self.help_action = QAction(CondetrolMainWindow)
        self.help_action.setObjectName("help_action")
        self.about_qt_action = QAction(CondetrolMainWindow)
        self.about_qt_action.setObjectName("about_qt_action")
        self.about_condetrol_action = QAction(CondetrolMainWindow)
        self.about_condetrol_action.setObjectName("about_condetrol_action")
        self.centralwidget = QWidget(CondetrolMainWindow)
        self.centralwidget.setObjectName("centralwidget")
        CondetrolMainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(CondetrolMainWindow)
        self.menubar.setObjectName("menubar")
        self.menubar.setGeometry(QRect(0, 0, 800, 33))
        self.device_configurations_menu = QMenu(self.menubar)
        self.device_configurations_menu.setObjectName("device_configurations_menu")
        self.dock_menu = QMenu(self.menubar)
        self.dock_menu.setObjectName("dock_menu")
        self.menuhelp = QMenu(self.menubar)
        self.menuhelp.setObjectName("menuhelp")
        CondetrolMainWindow.setMenuBar(self.menubar)

        self.menubar.addAction(self.device_configurations_menu.menuAction())
        self.menubar.addAction(self.dock_menu.menuAction())
        self.menubar.addAction(self.menuhelp.menuAction())
        self.device_configurations_menu.addAction(
            self.action_edit_device_configurations
        )
        self.menuhelp.addAction(self.help_action)
        self.menuhelp.addSeparator()
        self.menuhelp.addAction(self.about_condetrol_action)
        self.menuhelp.addAction(self.about_qt_action)

        self.retranslateUi(CondetrolMainWindow)

        QMetaObject.connectSlotsByName(CondetrolMainWindow)

    # setupUi

    def retranslateUi(self, CondetrolMainWindow):
        CondetrolMainWindow.setWindowTitle("")
        self.action_edit_device_configurations.setText(
            QCoreApplication.translate("CondetrolMainWindow", "Edit...", None)
        )
        self.actionExport.setText(
            QCoreApplication.translate("CondetrolMainWindow", "Export...", None)
        )
        self.actionLoad.setText(
            QCoreApplication.translate("CondetrolMainWindow", "Load...", None)
        )
        self.action_edit_constants.setText(
            QCoreApplication.translate("CondetrolMainWindow", "Edit...", None)
        )
        self.help_action.setText(
            QCoreApplication.translate("CondetrolMainWindow", "Condetrol help", None)
        )
        # if QT_CONFIG(shortcut)
        self.help_action.setShortcut(
            QCoreApplication.translate("CondetrolMainWindow", "F1", None)
        )
        # endif // QT_CONFIG(shortcut)
        self.about_qt_action.setText(
            QCoreApplication.translate("CondetrolMainWindow", "About Qt", None)
        )
        self.about_condetrol_action.setText(
            QCoreApplication.translate("CondetrolMainWindow", "About Condetrol", None)
        )
        self.device_configurations_menu.setTitle(
            QCoreApplication.translate("CondetrolMainWindow", "Devices", None)
        )
        self.dock_menu.setTitle(
            QCoreApplication.translate("CondetrolMainWindow", "Docks", None)
        )
        self.menuhelp.setTitle(
            QCoreApplication.translate("CondetrolMainWindow", "Help", None)
        )

    # retranslateUi
