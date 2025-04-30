from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtGui import QWheelEvent
from PyQt5.QtWidgets import QGraphicsView


class MotionGraphicsView(QGraphicsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._zoom = 0
        self._default_transform = self.transform()

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() == Qt.ControlModifier:
            angle = event.angleDelta().y()
            factor = 1.25 if angle > 0 else 0.8
            self.zoom_at(event.pos(), factor)
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton and event.modifiers() == Qt.ControlModifier:
            self.reset_zoom_at(event.pos())
        else:
            super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
                self.zoom_at_center(1.25)
            elif event.key() == Qt.Key_Minus:
                self.zoom_at_center(0.8)
            elif event.key() == Qt.Key_0:
                self.reset_zoom_at_center()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def zoom_at(self, pos, factor):
        old_pos = self.mapToScene(pos)
        self.scale(factor, factor)
        new_pos = self.mapToScene(pos)
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())

    def zoom_at_center(self, factor):
        center = self.viewport().rect().center()
        self.zoom_at(center, factor)

    def reset_zoom_at(self, pos):
        self.setTransform(self._default_transform)
        self._zoom = 0
        self.centerOn(self.mapToScene(pos))

    def reset_zoom_at_center(self):
        self.setTransform(self._default_transform)
        self._zoom = 0
