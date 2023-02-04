import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    color: "transparent"
GridLayout {
    anchors.fill: parent
    columns: 3
    Label { text: "Board number"; Layout.minimumWidth: implicitWidth }
    SpinBox {
        id: boardNumber
        editable: true
        from: 0
        Layout.maximumWidth: implicitWidth
    }
    Item { Layout.fillWidth: true }
    Label { text: "Timestep"}
}
}