# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'configurations_editor.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QHBoxLayout, QPushButton, QSizePolicy, QTabWidget,
    QVBoxLayout, QWidget)

class Ui_ConfigurationsEditor(object):
    def setupUi(self, ConfigurationsEditor):
        if not ConfigurationsEditor.objectName():
            ConfigurationsEditor.setObjectName(u"ConfigurationsEditor")
        ConfigurationsEditor.resize(414, 300)
        self.verticalLayout = QVBoxLayout(ConfigurationsEditor)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tab_widget = QTabWidget(ConfigurationsEditor)
        self.tab_widget.setObjectName(u"tab_widget")
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(False)
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.tab_widget.addTab(self.tab, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.tab_widget.addTab(self.tab_2, "")

        self.verticalLayout.addWidget(self.tab_widget)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(6)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.add_device_button = QPushButton(ConfigurationsEditor)
        self.add_device_button.setObjectName(u"add_device_button")

        self.horizontalLayout.addWidget(self.add_device_button)

        self.buttonBox = QDialogButtonBox(ConfigurationsEditor)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.horizontalLayout.addWidget(self.buttonBox)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.retranslateUi(ConfigurationsEditor)
        self.buttonBox.accepted.connect(ConfigurationsEditor.accept)
        self.buttonBox.rejected.connect(ConfigurationsEditor.reject)

        self.tab_widget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(ConfigurationsEditor)
    # setupUi

    def retranslateUi(self, ConfigurationsEditor):
        ConfigurationsEditor.setWindowTitle(QCoreApplication.translate("ConfigurationsEditor", u"Edit device configurations...", None))
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.tab), QCoreApplication.translate("ConfigurationsEditor", u"Tab 1", None))
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.tab_2), QCoreApplication.translate("ConfigurationsEditor", u"Tab 2", None))
        self.add_device_button.setText(QCoreApplication.translate("ConfigurationsEditor", u"Add device...", None))
    # retranslateUi

