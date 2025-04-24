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


class FrameBlockItem(QGraphicsRectItem):
    def __init__(self, frame_name, uid=None):
        temp_label = QGraphicsTextItem(frame_name)
        font_metrics = QFontMetricsF(temp_label.font())
        text_width = font_metrics.width(frame_name)
        width = max(120, text_width + 20)
        height = 60

        super().__init__(0, 0, width, height)
        self.setBrush(QBrush(QColor("#1a1a1a")))
        self.default_pen = QPen(QColor("#ffffff"))
        self.selected_pen = QPen(QColor("#00ffff"))
        self.default_pen.setWidth(3)
        self.selected_pen.setWidth(4)
        self.setPen(self.default_pen)

        self.setFlags(self.ItemIsMovable | self.ItemIsSelectable)
        self.name = frame_name
        self.uid = uid if uid is not None else frame_name

        self.label = QGraphicsTextItem(frame_name, self)
        self.label.setDefaultTextColor(QColor("white"))
        label_width = self.label.boundingRect().width()
        label_height = self.label.boundingRect().height()
        self.label.setPos((width - label_width) / 2, (height - label_height) / 2)

        self.connection = {"output": {}}

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
            print(f"Edit Frame: {self.name} (id: {self.uid})")
        elif selected_action == delete_action:
            scene = self.scene()
            if scene:
                scene.removeItem(self)
        elif selected_action == connect_action:
            print(f"Connect from: {self.name} (id: {self.uid})")

    def paint(self, painter, option, widget=None):
        self.setPen(self.selected_pen if self.isSelected() else self.default_pen)
        super().paint(painter, option, widget)


class MotionFlowScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundBrush(QColor("#111111"))
        self.id_counter = 0

    def _generate_uid(self, name):
        safe = "".join(c if c.isalnum() else "_" for c in name)
        uid = f"frame_{safe}_id{self.id_counter:03}"
        self.id_counter += 1
        return uid

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        name = event.mimeData().text()
        pos = event.scenePos()
        uid = self._generate_uid(name)
        item = FrameBlockItem(name, uid=uid)
        item.setPos(pos)
        self.addItem(item)
        event.acceptProposedAction()

    def contextMenuEvent(self, event):
        item = self.itemAt(event.scenePos(), self.views()[0].transform())
        if item and isinstance(item, FrameBlockItem):
            item.setSelected(True)
            item.contextMenuEvent(event)
        else:
            menu = QMenu()
            add_frame_action = QAction("Add New Frame", menu)
            menu.addAction(add_frame_action)
            selected_action = menu.exec_(event.screenPos())
            if selected_action == add_frame_action:
                print("New Frame block requested")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            for item in self.selectedItems():
                self.removeItem(item)
        else:
            super().keyPressEvent(event)

    def add_if_condition_block(self, pos):
        existing_names = [item.name for item in self.items() if hasattr(item, "condition") and hasattr(item, "name")]
        dialog = IfConditionExpressionDialog(
            available_variables=self.available_variables,
            frame_names=self.get_all_frame_names(),
            existing_names=existing_names
        )
        if dialog.exec_():
            result = dialog.result
            uid = self._generate_uid(result["name"])
            block = FrameBlockItem(result["name"], uid=uid)
            block.setPos(pos)
            block.label.setPlainText(f"if:\n{result['condition']}")
            block.condition = result["condition"]
            block.to_true = result["to_true"]
            block.to_false = result["to_false"]
            block.name = result["name"]
            self.addItem(block)

    def get_all_frame_names(self):
        return [item.name for item in self.items() if isinstance(item, FrameBlockItem)]

    def to_layout_dict(self):
        layout = {"block": {}, "arrow": {}}
        block_id_counter = 0
        arrow_id_counter = 0
        used_uids = set()

        print("\n[DEBUG] Items in scene:")
        for item in self.items():
            print(f" - {type(item)} uid={getattr(item, 'uid', None)} name={getattr(item, 'name', None)}")

        for item in self.items():
            if isinstance(item, FrameBlockItem):
                if not hasattr(item, 'uid') or not item.uid:
                    item.uid = self._generate_uid(item.name)
                while item.uid in used_uids:
                    item.uid = self._generate_uid(item.name)
                used_uids.add(item.uid)

                uid = item.uid
                layout["block"][uid] = {
                    "info": {
                        "type": "frame",
                        "filename": item.name,
                        "id": block_id_counter
                    },
                    "place": {
                        "x": int(item.pos().x()),
                        "y": int(item.pos().y())
                    },
                    "connection": item.connection if hasattr(item, "connection") else {"output": {}}
                }
                print(f"[DEBUG] Block saved: {uid} at ({item.pos().x()}, {item.pos().y()})")
                block_id_counter += 1

        print("[DEBUG] Block count to save:", len(layout["block"]))
        return layout

    def load_layout_dict(self, layout):
        self.clear()
        for uid, block in layout.get("block", {}).items():
            name = block["info"]["filename"]
            x = block["place"]["x"]
            y = block["place"]["y"]
            item = FrameBlockItem(name, uid=uid)
            item.setPos(x, y)
            if "connection" in block:
                item.connection = block["connection"]
            self.addItem(item)
