# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'single_shot_widget.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
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
    QDockWidget,
    QHeaderView,
    QMainWindow,
    QMdiArea,
    QMenu,
    QMenuBar,
    QSizePolicy,
    QTreeView,
    QVBoxLayout,
    QWidget,
)


class Ui_SingleShotWidget(object):
    def setupUi(self, SingleShotWidget):
        if not SingleShotWidget.objectName():
            SingleShotWidget.setObjectName("SingleShotWidget")
        SingleShotWidget.resize(800, 600)
        self._action_cascade = QAction(SingleShotWidget)
        self._action_cascade.setObjectName("_action_cascade")
        self._action_tile = QAction(SingleShotWidget)
        self._action_tile.setObjectName("_action_tile")
        self.actionImage = QAction(SingleShotWidget)
        self.actionImage.setObjectName("actionImage")
        self.actionParameters = QAction(SingleShotWidget)
        self.actionParameters.setObjectName("actionParameters")
        self.actionAtoms = QAction(SingleShotWidget)
        self.actionAtoms.setObjectName("actionAtoms")
        self.actionSave = QAction(SingleShotWidget)
        self.actionSave.setObjectName("actionSave")
        self.actionSave_as = QAction(SingleShotWidget)
        self.actionSave_as.setObjectName("actionSave_as")
        self.actionLoad = QAction(SingleShotWidget)
        self.actionLoad.setObjectName("actionLoad")
        self.centralwidget = QWidget(SingleShotWidget)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self._mdi_area = QMdiArea(self.centralwidget)
        self._mdi_area.setObjectName("_mdi_area")

        self.verticalLayout.addWidget(self._mdi_area)

        SingleShotWidget.setCentralWidget(self.centralwidget)
        self.menuBar = QMenuBar(SingleShotWidget)
        self.menuBar.setObjectName("menuBar")
        self.menuBar.setGeometry(QRect(0, 0, 800, 21))
        self.menuWindow = QMenu(self.menuBar)
        self.menuWindow.setObjectName("menuWindow")
        self.menu_add_viewer = QMenu(self.menuBar)
        self.menu_add_viewer.setObjectName("menu_add_viewer")
        self.menuWorkspace = QMenu(self.menuBar)
        self.menuWorkspace.setObjectName("menuWorkspace")
        SingleShotWidget.setMenuBar(self.menuBar)
        self._shot_selector_dock = QDockWidget(SingleShotWidget)
        self._shot_selector_dock.setObjectName("_shot_selector_dock")
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self._shot_selector_dock.sizePolicy().hasHeightForWidth()
        )
        self._shot_selector_dock.setSizePolicy(sizePolicy)
        self._shot_selector_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.dockWidgetContents = QWidget()
        self.dockWidgetContents.setObjectName("dockWidgetContents")
        self._shot_selector_dock.setWidget(self.dockWidgetContents)
        SingleShotWidget.addDockWidget(Qt.TopDockWidgetArea, self._shot_selector_dock)
        self._sequence_hierarchy_dock = QDockWidget(SingleShotWidget)
        self._sequence_hierarchy_dock.setObjectName("_sequence_hierarchy_dock")
        self._sequence_hierarchy_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.dockWidgetContents_2 = QWidget()
        self.dockWidgetContents_2.setObjectName("dockWidgetContents_2")
        self.verticalLayout_2 = QVBoxLayout(self.dockWidgetContents_2)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self._sequence_hierarchy_view = QTreeView(self.dockWidgetContents_2)
        self._sequence_hierarchy_view.setObjectName("_sequence_hierarchy_view")

        self.verticalLayout_2.addWidget(self._sequence_hierarchy_view)

        self._sequence_hierarchy_dock.setWidget(self.dockWidgetContents_2)
        SingleShotWidget.addDockWidget(
            Qt.LeftDockWidgetArea, self._sequence_hierarchy_dock
        )

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
        SingleShotWidget.setWindowTitle(
            QCoreApplication.translate("SingleShotWidget", "MainWindow", None)
        )
        self._action_cascade.setText(
            QCoreApplication.translate("SingleShotWidget", "Cascade", None)
        )
        self._action_tile.setText(
            QCoreApplication.translate("SingleShotWidget", "Tile", None)
        )
        self.actionImage.setText(
            QCoreApplication.translate("SingleShotWidget", "Image", None)
        )
        self.actionParameters.setText(
            QCoreApplication.translate("SingleShotWidget", "Parameters", None)
        )
        self.actionAtoms.setText(
            QCoreApplication.translate("SingleShotWidget", "Atoms", None)
        )
        self.actionSave.setText(
            QCoreApplication.translate("SingleShotWidget", "Save", None)
        )
        self.actionSave_as.setText(
            QCoreApplication.translate("SingleShotWidget", "Save as", None)
        )
        self.actionLoad.setText(
            QCoreApplication.translate("SingleShotWidget", "Load", None)
        )
        self.menuWindow.setTitle(
            QCoreApplication.translate("SingleShotWidget", "Windows", None)
        )
        self.menu_add_viewer.setTitle(
            QCoreApplication.translate("SingleShotWidget", "Add viewer", None)
        )
        self.menuWorkspace.setTitle(
            QCoreApplication.translate("SingleShotWidget", "Workspace", None)
        )

    # retranslateUi
