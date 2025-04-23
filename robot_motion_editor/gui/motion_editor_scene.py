# motion_editor_scene.py
from PyQt5.QtCore import QPointF
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsRectItem
from PyQt5.QtWidgets import QGraphicsScene
from PyQt5.QtWidgets import QGraphicsTextItem


class FrameBlockItem(QGraphicsRectItem):
    def __init__(self, frame_name):
        super().__init__(0, 0, 120, 60)
        self.setBrush(QBrush(QColor("lightblue")))
        self.setFlags(
            self.ItemIsMovable
            | self.ItemIsSelectable
        )
        self.name = frame_name

        # Add label to display frame name
        self.label = QGraphicsTextItem(frame_name, self)
        self.label.setDefaultTextColor(QColor("black"))
        self.label.setPos(10, 20)


class MotionFlowScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundBrush(QColor(250, 250, 250))

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
