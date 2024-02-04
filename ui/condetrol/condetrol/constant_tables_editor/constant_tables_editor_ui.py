# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'constant_tables_editor.ui'
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

class Ui_ConstantTablesEditor(object):
    def setupUi(self, ConstantTablesEditor):
        if not ConstantTablesEditor.objectName():
            ConstantTablesEditor.setObjectName(u"ConstantTablesEditor")
        ConstantTablesEditor.resize(607, 300)
        self.verticalLayout = QVBoxLayout(ConstantTablesEditor)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tab_widget = QTabWidget(ConstantTablesEditor)
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
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.add_button = QPushButton(ConstantTablesEditor)
        self.add_button.setObjectName(u"add_button")

        self.horizontalLayout.addWidget(self.add_button)

        self.buttonBox = QDialogButtonBox(ConstantTablesEditor)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.horizontalLayout.addWidget(self.buttonBox)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.retranslateUi(ConstantTablesEditor)
        self.buttonBox.accepted.connect(ConstantTablesEditor.accept)
        self.buttonBox.rejected.connect(ConstantTablesEditor.reject)

        self.tab_widget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(ConstantTablesEditor)
    # setupUi

    def retranslateUi(self, ConstantTablesEditor):
        ConstantTablesEditor.setWindowTitle(QCoreApplication.translate("ConstantTablesEditor", u"Edit constant tables...", None))
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.tab), QCoreApplication.translate("ConstantTablesEditor", u"Tab 1", None))
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.tab_2), QCoreApplication.translate("ConstantTablesEditor", u"Tab 2", None))
        self.add_button.setText(QCoreApplication.translate("ConstantTablesEditor", u"Add table...", None))
    # retranslateUi

