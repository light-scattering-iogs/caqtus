# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'scatter_view.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit,
    QSizePolicy, QSpacerItem, QToolButton, QVBoxLayout,
    QWidget)

class Ui_ScatterView(object):
    def setupUi(self, ScatterView):
        if not ScatterView.objectName():
            ScatterView.setObjectName(u"ScatterView")
        ScatterView.resize(400, 300)
        self.verticalLayout = QVBoxLayout(ScatterView)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(ScatterView)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.x_line_edit = QLineEdit(ScatterView)
        self.x_line_edit.setObjectName(u"x_line_edit")

        self.horizontalLayout.addWidget(self.x_line_edit)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.label_2 = QLabel(ScatterView)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout.addWidget(self.label_2)

        self.y_line_edit = QLineEdit(ScatterView)
        self.y_line_edit.setObjectName(u"y_line_edit")

        self.horizontalLayout.addWidget(self.y_line_edit)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.apply_button = QToolButton(ScatterView)
        self.apply_button.setObjectName(u"apply_button")

        self.horizontalLayout.addWidget(self.apply_button)

        self.settings_button = QToolButton(ScatterView)
        self.settings_button.setObjectName(u"settings_button")

        self.horizontalLayout.addWidget(self.settings_button)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.retranslateUi(ScatterView)

        QMetaObject.connectSlotsByName(ScatterView)
    # setupUi

    def retranslateUi(self, ScatterView):
        ScatterView.setWindowTitle(QCoreApplication.translate("ScatterView", u"Form", None))
        self.label.setText(QCoreApplication.translate("ScatterView", u"x:", None))
        self.label_2.setText(QCoreApplication.translate("ScatterView", u"y:", None))
        self.apply_button.setText(QCoreApplication.translate("ScatterView", u"...", None))
        self.settings_button.setText(QCoreApplication.translate("ScatterView", u"...", None))
    # retranslateUi

