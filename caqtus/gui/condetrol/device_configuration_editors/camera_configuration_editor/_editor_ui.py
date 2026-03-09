# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'editor.ui'
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
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QWidget,
)


class Ui_CameraConfigurationEditor(object):
    def setupUi(self, CameraConfigurationEditor):
        if not CameraConfigurationEditor.objectName():
            CameraConfigurationEditor.setObjectName("CameraConfigurationEditor")
        CameraConfigurationEditor.resize(424, 549)
        self.horizontalLayout = QHBoxLayout(CameraConfigurationEditor)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.form = QFormLayout()
        self.form.setObjectName("form")
        self.label_2 = QLabel(CameraConfigurationEditor)
        self.label_2.setObjectName("label_2")

        self.form.setWidget(0, QFormLayout.LabelRole, self.label_2)

        self.formLayout_3 = QFormLayout()
        self.formLayout_3.setObjectName("formLayout_3")
        self.formLayout_3.setVerticalSpacing(6)
        self.formLayout_3.setContentsMargins(-1, 5, -1, -1)
        self.xLabel = QLabel(CameraConfigurationEditor)
        self.xLabel.setObjectName("xLabel")

        self.formLayout_3.setWidget(0, QFormLayout.LabelRole, self.xLabel)

        self._left_spinbox = QSpinBox(CameraConfigurationEditor)
        self._left_spinbox.setObjectName("_left_spinbox")

        self.formLayout_3.setWidget(0, QFormLayout.FieldRole, self._left_spinbox)

        self.widthLabel = QLabel(CameraConfigurationEditor)
        self.widthLabel.setObjectName("widthLabel")

        self.formLayout_3.setWidget(1, QFormLayout.LabelRole, self.widthLabel)

        self._right_spinbox = QSpinBox(CameraConfigurationEditor)
        self._right_spinbox.setObjectName("_right_spinbox")

        self.formLayout_3.setWidget(1, QFormLayout.FieldRole, self._right_spinbox)

        self.yLabel = QLabel(CameraConfigurationEditor)
        self.yLabel.setObjectName("yLabel")

        self.formLayout_3.setWidget(2, QFormLayout.LabelRole, self.yLabel)

        self._bottom_spinbox = QSpinBox(CameraConfigurationEditor)
        self._bottom_spinbox.setObjectName("_bottom_spinbox")

        self.formLayout_3.setWidget(2, QFormLayout.FieldRole, self._bottom_spinbox)

        self.heightLabel = QLabel(CameraConfigurationEditor)
        self.heightLabel.setObjectName("heightLabel")

        self.formLayout_3.setWidget(3, QFormLayout.LabelRole, self.heightLabel)

        self._top_spinbox = QSpinBox(CameraConfigurationEditor)
        self._top_spinbox.setObjectName("_top_spinbox")

        self.formLayout_3.setWidget(3, QFormLayout.FieldRole, self._top_spinbox)

        self.form.setLayout(0, QFormLayout.FieldRole, self.formLayout_3)

        self.horizontalLayout.addLayout(self.form)

        self.horizontalSpacer = QSpacerItem(
            40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum
        )

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.horizontalLayout.setStretch(1, 1)

        self.retranslateUi(CameraConfigurationEditor)

        QMetaObject.connectSlotsByName(CameraConfigurationEditor)

    # setupUi

    def retranslateUi(self, CameraConfigurationEditor):
        CameraConfigurationEditor.setWindowTitle(
            QCoreApplication.translate("CameraConfigurationEditor", "Form", None)
        )
        # if QT_CONFIG(tooltip)
        self.label_2.setToolTip(
            QCoreApplication.translate(
                "CameraConfigurationEditor",
                "<html><head/><body><p>Rectangular region of interest to extract from the full sensor picture.</p></body></html>",
                None,
            )
        )
        # endif // QT_CONFIG(tooltip)
        self.label_2.setText(
            QCoreApplication.translate("CameraConfigurationEditor", "ROI", None)
        )
        self.xLabel.setText(
            QCoreApplication.translate("CameraConfigurationEditor", "Left", None)
        )
        self.widthLabel.setText(
            QCoreApplication.translate("CameraConfigurationEditor", "Right", None)
        )
        self.yLabel.setText(
            QCoreApplication.translate("CameraConfigurationEditor", "Bottom", None)
        )
        self.heightLabel.setText(
            QCoreApplication.translate("CameraConfigurationEditor", "Top", None)
        )

    # retranslateUi
