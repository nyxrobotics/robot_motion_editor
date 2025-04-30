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
        if item and item.parent():
            parent_text = item.parent().text(0)
            grand_parent_text = item.parent().parent().text(0) if item.parent().parent() else ""

            # ドラッグ対象の種別判定
            if parent_text == "frames":
                item_type = "frame"
            elif parent_text == "if":
                item_type = "if"
            elif parent_text == "switch":
                item_type = "switch"
            else:
                event.ignore()
                return

            mime_text = f"{item_type}:{item.text(0)}"
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(mime_text)
            drag.setMimeData(mime)
            drag.exec_(Qt.CopyAction)
        else:
            event.ignore()
