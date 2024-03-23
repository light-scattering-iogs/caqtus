# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'single_shot_widget.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
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
from PySide6.QtWidgets import (QApplication, QDockWidget, QHeaderView, QMainWindow,
    QMdiArea, QMenu, QMenuBar, QSizePolicy,
    QTreeView, QVBoxLayout, QWidget)

class Ui_SingleShotWidget(object):
    def setupUi(self, SingleShotWidget):
        if not SingleShotWidget.objectName():
            SingleShotWidget.setObjectName(u"SingleShotWidget")
        SingleShotWidget.resize(800, 600)
        self._action_cascade = QAction(SingleShotWidget)
        self._action_cascade.setObjectName(u"_action_cascade")
        self._action_tile = QAction(SingleShotWidget)
        self._action_tile.setObjectName(u"_action_tile")
        self.actionImage = QAction(SingleShotWidget)
        self.actionImage.setObjectName(u"actionImage")
        self.actionParameters = QAction(SingleShotWidget)
        self.actionParameters.setObjectName(u"actionParameters")
        self.actionAtoms = QAction(SingleShotWidget)
        self.actionAtoms.setObjectName(u"actionAtoms")
        self.actionSave = QAction(SingleShotWidget)
        self.actionSave.setObjectName(u"actionSave")
        self.actionSave_as = QAction(SingleShotWidget)
        self.actionSave_as.setObjectName(u"actionSave_as")
        self.actionLoad = QAction(SingleShotWidget)
        self.actionLoad.setObjectName(u"actionLoad")
        self.centralwidget = QWidget(SingleShotWidget)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self._mdi_area = QMdiArea(self.centralwidget)
        self._mdi_area.setObjectName(u"_mdi_area")

        self.verticalLayout.addWidget(self._mdi_area)

        SingleShotWidget.setCentralWidget(self.centralwidget)
        self.menuBar = QMenuBar(SingleShotWidget)
        self.menuBar.setObjectName(u"menuBar")
        self.menuBar.setGeometry(QRect(0, 0, 800, 21))
        self.menuWindow = QMenu(self.menuBar)
        self.menuWindow.setObjectName(u"menuWindow")
        self.menu_add_viewer = QMenu(self.menuBar)
        self.menu_add_viewer.setObjectName(u"menu_add_viewer")
        self.menuWorkspace = QMenu(self.menuBar)
        self.menuWorkspace.setObjectName(u"menuWorkspace")
        SingleShotWidget.setMenuBar(self.menuBar)
        self._shot_selector_dock = QDockWidget(SingleShotWidget)
        self._shot_selector_dock.setObjectName(u"_shot_selector_dock")
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self._shot_selector_dock.sizePolicy().hasHeightForWidth())
        self._shot_selector_dock.setSizePolicy(sizePolicy)
        self._shot_selector_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.dockWidgetContents = QWidget()
        self.dockWidgetContents.setObjectName(u"dockWidgetContents")
        self._shot_selector_dock.setWidget(self.dockWidgetContents)
        SingleShotWidget.addDockWidget(Qt.TopDockWidgetArea, self._shot_selector_dock)
        self._sequence_hierarchy_dock = QDockWidget(SingleShotWidget)
        self._sequence_hierarchy_dock.setObjectName(u"_sequence_hierarchy_dock")
        self._sequence_hierarchy_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.dockWidgetContents_2 = QWidget()
        self.dockWidgetContents_2.setObjectName(u"dockWidgetContents_2")
        self.verticalLayout_2 = QVBoxLayout(self.dockWidgetContents_2)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self._sequence_hierarchy_view = QTreeView(self.dockWidgetContents_2)
        self._sequence_hierarchy_view.setObjectName(u"_sequence_hierarchy_view")

        self.verticalLayout_2.addWidget(self._sequence_hierarchy_view)

        self._sequence_hierarchy_dock.setWidget(self.dockWidgetContents_2)
        SingleShotWidget.addDockWidget(Qt.LeftDockWidgetArea, self._sequence_hierarchy_dock)

        self.menuBar.addAction(self.menuWorkspace.menuAction())
        self.menuBar.addAction(self.menu_add_viewer.menuAction())
        self.menuBar.addAction(self.menuWindow.menuAction())
        self.menuWindow.addAction(self._action_cascade)
        self.menuWindow.addAction(self._action_tile)
        self.menuWorkspace.addAction(self.actionSave_as)
        self.menuWorkspace.addAction(self.actionLoad)

        self.retranslateUi(SingleShotWidget)

        QMetaObject.connectSlotsByName(SingleShotWidget)
    # setupUi

    def retranslateUi(self, SingleShotWidget):
        SingleShotWidget.setWindowTitle(QCoreApplication.translate("SingleShotWidget", u"MainWindow", None))
        self._action_cascade.setText(QCoreApplication.translate("SingleShotWidget", u"Cascade", None))
        self._action_tile.setText(QCoreApplication.translate("SingleShotWidget", u"Tile", None))
        self.actionImage.setText(QCoreApplication.translate("SingleShotWidget", u"Image", None))
        self.actionParameters.setText(QCoreApplication.translate("SingleShotWidget", u"Parameters", None))
        self.actionAtoms.setText(QCoreApplication.translate("SingleShotWidget", u"Atoms", None))
        self.actionSave.setText(QCoreApplication.translate("SingleShotWidget", u"Save", None))
        self.actionSave_as.setText(QCoreApplication.translate("SingleShotWidget", u"Save as", None))
        self.actionLoad.setText(QCoreApplication.translate("SingleShotWidget", u"Load", None))
        self.menuWindow.setTitle(QCoreApplication.translate("SingleShotWidget", u"Windows", None))
        self.menu_add_viewer.setTitle(QCoreApplication.translate("SingleShotWidget", u"Add viewer", None))
        self.menuWorkspace.setTitle(QCoreApplication.translate("SingleShotWidget", u"Workspace", None))
    # retranslateUi

