from PyQt5.QtCore import QPointF
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush
from PyQt5.QtGui import QColor
from PyQt5.QtGui import QFontMetricsF
from PyQt5.QtGui import QPen
from PyQt5.QtWidgets import QAction
from PyQt5.QtWidgets import QGraphicsRectItem
from PyQt5.QtWidgets import QGraphicsScene
from PyQt5.QtWidgets import QGraphicsTextItem
from PyQt5.QtWidgets import QMenu

from .if_condition_editor import IfConditionExpressionDialog


class FrameBlockItem(QGraphicsRectItem):
    def __init__(self, frame_name):
        temp_label = QGraphicsTextItem(frame_name)
        font_metrics = QFontMetricsF(temp_label.font())
        text_width = font_metrics.width(frame_name)
        width = max(120, text_width + 20)
        height = 60

        super().__init__(0, 0, width, height)
        self.setBrush(QBrush(QColor("#1a1a1a")))
        pen = QPen(QColor("#ffffff"))
        pen.setWidth(2)
        self.setPen(pen)
        self.setFlags(self.ItemIsMovable | self.ItemIsSelectable)
        self.name = frame_name

        self.label = QGraphicsTextItem(frame_name, self)
        self.label.setDefaultTextColor(QColor("white"))
        label_width = self.label.boundingRect().width()
        label_height = self.label.boundingRect().height()
        self.label.setPos((width - label_width) / 2, (height - label_height) / 2)

    def contextMenuEvent(self, event):
        menu = QMenu()
        edit_action = QAction("Edit Frame", menu)
        delete_action = QAction("Delete Block", menu)
        connect_action = QAction("Connect To...", menu)
        menu.addAction(edit_action)
        menu.addAction(delete_action)
        menu.addAction(connect_action)

        selected_action = menu.exec_(event.screenPos())
        if selected_action == edit_action:
            print(f"Edit Frame: {self.name}")
        elif selected_action == delete_action:
            scene = self.scene()
            if scene:
                scene.removeItem(self)
        elif selected_action == connect_action:
            print(f"Connect from: {self.name}")


class MotionFlowScene(QGraphicsScene):
    def __init__(self, available_variables=None, parent=None):
        super().__init__(parent)
        self.available_variables = available_variables or []
        self.setBackgroundBrush(QColor("#111111"))

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

    def contextMenuEvent(self, event):
        menu = QMenu()
        add_frame_action = QAction("Add New Frame", menu)
        add_existing_action = QAction("Add Existing Frame", menu)
        add_if_condition_action = QAction("Add If Condition", menu)
        menu.addAction(add_frame_action)
        menu.addAction(add_existing_action)
        menu.addAction(add_if_condition_action)

        selected_action = menu.exec_(event.screenPos())
        if selected_action == add_frame_action:
            print("New Frame block requested")
        elif selected_action == add_existing_action:
            print("Add Existing Frame requested")
        elif selected_action == add_if_condition_action:
            self.add_if_condition_block(event.scenePos())

    def add_if_condition_block(self, pos):
        dialog = IfConditionExpressionDialog(
            available_variables=self.available_variables,
            frame_names=self.get_all_frame_names()
        )
        if dialog.exec_():
            result = dialog.result
            block_name = f"if_{len(self.items())+1}"
            item = FrameBlockItem(block_name)
            item.label.setPlainText(f"if:{result['condition']}")
            item.setPos(pos)
            item.condition = result['condition']
            item.to_true = result['to_true']
            item.to_false = result['to_false']
            self.addItem(item)

    def get_all_frame_names(self):
        return [item.name for item in self.items() if isinstance(item, FrameBlockItem)]
