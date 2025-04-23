# motion_editor_scene.py
from PyQt5.QtCore import QPointF
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush
from PyQt5.QtGui import QColor
from PyQt5.QtGui import QFontMetricsF
from PyQt5.QtGui import QPen
from PyQt5.QtWidgets import QGraphicsRectItem
from PyQt5.QtWidgets import QGraphicsScene
from PyQt5.QtWidgets import QGraphicsTextItem


class FrameBlockItem(QGraphicsRectItem):
    def __init__(self, frame_name):
        # Create temporary text item to measure width
        temp_label = QGraphicsTextItem(frame_name)
        font_metrics = QFontMetricsF(temp_label.font())
        text_width = font_metrics.width(frame_name)
        width = max(120, text_width + 20)
        height = 60

        super().__init__(0, 0, width, height)
        self.setBrush(QBrush(QColor("#1a1a1a")))  # Darker block background
        pen = QPen(QColor("#ffffff"))  # Bright white border
        pen.setWidth(2)  # Thicker border
        self.setPen(pen)
        self.setFlags(
            self.ItemIsMovable
            | self.ItemIsSelectable
        )
        self.name = frame_name

        # Add label to display frame name, centered in box
        self.label = QGraphicsTextItem(frame_name, self)
        self.label.setDefaultTextColor(QColor("white"))
        label_width = self.label.boundingRect().width()
        label_height = self.label.boundingRect().height()
        self.label.setPos((width - label_width) / 2, (height - label_height) / 2)


class MotionFlowScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundBrush(QColor("#111111"))  # Darker theme background

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        name = event.mimeData().text()
        pos = event.scenePos()
        item = FrameBlockItem(name)
        item.setPos(pos)
        self.addItem(item)
        event.acceptProposedAction()
