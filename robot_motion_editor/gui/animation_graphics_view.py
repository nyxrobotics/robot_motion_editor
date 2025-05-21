from PyQt5.QtCore import QEvent
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtGui import QWheelEvent
from PyQt5.QtWidgets import QGraphicsView


class AnimatioGraphicsView(QGraphicsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._zoom = 0
        self._default_transform = self.transform()

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            # Ctrl + ホイール → 拡大縮小
            angle = event.angleDelta().y()
            factor = 1.25 if angle > 0 else 0.8
            self.zoom_at(event.pos(), factor)
        elif event.modifiers() == Qt.ShiftModifier:
            # Shift + ホイール → 横スクロール
            delta = event.angleDelta().y()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta)
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton and event.modifiers() == Qt.ControlModifier:
            self.reset_zoom_at(event.pos())
        elif event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            # QtはScrollHandDragで左クリックを要求するので偽装
            fake_event = QMouseEvent(
                QEvent.MouseButtonPress,
                event.localPos(),
                Qt.LeftButton,
                Qt.LeftButton,
                Qt.NoModifier
            )
            super().mousePressEvent(fake_event)
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            # QtはScrollHandDragで左クリックを要求するので偽装
            fake_event = QMouseEvent(
                QEvent.MouseButtonRelease,
                event.localPos(),
                Qt.LeftButton,
                Qt.LeftButton,
                Qt.NoModifier
            )
            super().mouseReleaseEvent(fake_event)
            self.setDragMode(QGraphicsView.NoDrag)  # 通常モードに戻す
        else:
            super().mouseReleaseEvent(event)

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
        self.setTransformationAnchor(QGraphicsView.NoAnchor)
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
