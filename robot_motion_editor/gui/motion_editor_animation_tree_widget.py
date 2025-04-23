from PyQt5.QtCore import QMimeData
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import QTreeWidget


class AnimationTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setSelectionMode(QTreeWidget.SingleSelection)

    def mouseMoveEvent(self, event):
        item = self.currentItem()
        if item and item.parent():  # Only allow dragging for frames (child items)
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(item.text(0))
            drag.setMimeData(mime)
            drag.exec_(Qt.CopyAction)
        else:
            event.ignore()
