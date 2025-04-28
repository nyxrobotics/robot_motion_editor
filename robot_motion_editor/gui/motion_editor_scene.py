import math

from PyQt5.QtCore import QPointF
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush
from PyQt5.QtGui import QColor
from PyQt5.QtGui import QFontMetricsF
from PyQt5.QtGui import QPainterPath
from PyQt5.QtGui import QPen
from PyQt5.QtWidgets import QAction
from PyQt5.QtWidgets import QGraphicsEllipseItem
from PyQt5.QtWidgets import QGraphicsPathItem
from PyQt5.QtWidgets import QGraphicsRectItem
from PyQt5.QtWidgets import QGraphicsScene
from PyQt5.QtWidgets import QGraphicsTextItem
from PyQt5.QtWidgets import QMenu


def compute_edge_point(center, target, width, height):
    dx = target.x() - center.x()
    dy = target.y() - center.y()
    if dx == 0 and dy == 0:
        return center
    scale = 0.5 / max(abs(dx) / width, abs(dy) / height)
    return QPointF(center.x() + dx * scale, center.y() + dy * scale)


class FrameBlockItem(QGraphicsRectItem):
    def __init__(self, frame_name, uid=None):
        temp_label = QGraphicsTextItem(frame_name)
        font_metrics = QFontMetricsF(temp_label.font())
        text_width = font_metrics.width(frame_name)
        width = max(120, text_width + 20)
        height = 60
        super().__init__(0, 0, width, height)
        self.setBrush(QBrush(QColor("#1a1a1a")))
        self.default_pen = QPen(QColor("#ffffff"), 3)
        self.highlight_pen = QPen(QColor("#00ff00"), 3)
        self.selected_pen = QPen(QColor("#00ffff"), 4)
        self.setPen(self.default_pen)
        self.setFlags(self.ItemIsMovable | self.ItemIsSelectable | self.ItemSendsGeometryChanges)

        self.name = frame_name
        self.uid = uid or frame_name
        self.label = QGraphicsTextItem(frame_name, self)
        self.label.setDefaultTextColor(QColor("white"))
        self.label.setPos((width - self.label.boundingRect().width()) / 2,
                          (height - self.label.boundingRect().height()) / 2)

        self.connection = {"output": {}}
        self.is_highlighted = False

        self.input_arrows = []       # 入力側：複数接続OK
        self.output_arrow = None     # 出力側：1本まで

    def set_highlighted(self, state):
        self.is_highlighted = state
        self.update()

    def paint(self, painter, option, widget=None):
        self.setPen(self.selected_pen if self.isSelected()
                    else self.highlight_pen if self.is_highlighted
                    else self.default_pen)
        super().paint(painter, option, widget)

    def itemChange(self, change, value):
        if change == self.ItemPositionChange and self.scene():
            for item in self.scene().items():
                if isinstance(item, ArrowItem):
                    if item.start_item == self:
                        item._force_snap_start = True
                    if item.end_item == self:
                        item._force_snap_end = True
                    if item.start_item == self or item.end_item == self:
                        item.update_path()
        return super().itemChange(change, value)


class OutputSubBlockItem(QGraphicsRectItem):
    def __init__(self, label, parent_block):
        self.label_text = label
        temp_label = QGraphicsTextItem(label)
        font_metrics = QFontMetricsF(temp_label.font())
        text_width = font_metrics.width(label)
        text_height = font_metrics.height()

        width = max(100, text_width + 20)
        height = max(30, text_height + 10)

        super().__init__(0, 0, width, height)
        self.setBrush(QBrush(QColor("#2b2b2b")))
        self.default_pen = QPen(QColor("#aaaaaa"), 2)
        self.selected_pen = QPen(QColor("#00ffff"), 3)
        self.setPen(self.default_pen)
        self.setFlags(self.ItemIsSelectable | self.ItemSendsGeometryChanges)

        self.label = QGraphicsTextItem(label, self)
        self.label.setDefaultTextColor(QColor("white"))
        self.label.setPos((width - self.label.boundingRect().width()) / 2,
                          (height - self.label.boundingRect().height()) / 2)

        self.parent_block = parent_block  # 親ブロック (IfBlockItemやSwitchBlockItem)
        self.label = label      # "True", "False", "case_0"など
        self.output_arrow = None          # 必ず1本の出力Arrowを持つ

    def paint(self, painter, option, widget=None):
        self.setPen(self.selected_pen if self.isSelected() else self.default_pen)
        super().paint(painter, option, widget)

    def itemChange(self, change, value):
        if change == self.ItemPositionChange and self.scene():
            if self.output_arrow:
                self.output_arrow._force_snap_start = True
                self.output_arrow.update_path()
        return super().itemChange(change, value)


class IfBlockItem(QGraphicsRectItem):
    def __init__(self, block_name, uid=None):
        temp_label = QGraphicsTextItem(block_name)
        font_metrics = QFontMetricsF(temp_label.font())
        text_width = font_metrics.width(block_name)
        width = max(120, text_width + 20)
        super().__init__(0, 0, width, 60)
        self.setBrush(QBrush(QColor("#1a1a1a")))
        self.default_pen = QPen(QColor("#ffffff"), 3)
        self.highlight_pen = QPen(QColor("#00ff00"), 3)
        self.selected_pen = QPen(QColor("#00ffff"), 4)
        self.setPen(self.default_pen)
        self.setFlags(self.ItemIsMovable | self.ItemIsSelectable | self.ItemSendsGeometryChanges)

        self.name = block_name
        self.uid = uid or block_name

        self.label = QGraphicsTextItem(block_name, self)
        self.label.setDefaultTextColor(QColor("white"))
        self.label.setPos((width - self.label.boundingRect().width()) / 2, 5)
        self.is_highlighted = False
        self.outputs = {}
        self.create_output_blocks()

    def create_output_blocks(self):
        outputs = ["True", "False"]
        font_metrics = QFontMetricsF(self.label.font())
        text_height = font_metrics.height()
        gap = text_height / 2
        y = self.label.boundingRect().height() + 10

        for out_label in outputs:
            block = OutputSubBlockItem(out_label, self)
            block.setPos(10, y)
            self.outputs[out_label] = block
            if self.scene():
                self.scene().addItem(block)
            else:
                block.setParentItem(self)
            y += block.rect().height() + gap

        total_height = y
        self.setRect(0, 0, self.rect().width(), total_height)

    def set_highlighted(self, state):
        self.is_highlighted = state
        self.update()

    def paint(self, painter, option, widget=None):
        self.setPen(self.selected_pen if self.isSelected() else
                    self.highlight_pen if self.is_highlighted else
                    self.default_pen)
        super().paint(painter, option, widget)

    def itemChange(self, change, value):
        if change == self.ItemPositionChange and self.scene():
            for output in self.outputs.values():
                if output.output_arrow:
                    output.output_arrow._force_snap_start = True
                    output.output_arrow.update_path()
        return super().itemChange(change, value)


class SwitchBlockItem(QGraphicsRectItem):
    def __init__(self, block_name, num_cases=3, uid=None):
        temp_label = QGraphicsTextItem(block_name)
        font_metrics = QFontMetricsF(temp_label.font())
        text_width = font_metrics.width(block_name)
        width = max(120, text_width + 20)
        super().__init__(0, 0, width, 60)
        self.setBrush(QBrush(QColor("#1a1a1a")))
        self.default_pen = QPen(QColor("#ffffff"), 3)
        self.highlight_pen = QPen(QColor("#00ff00"), 3)
        self.selected_pen = QPen(QColor("#00ffff"), 4)
        self.setPen(self.default_pen)
        self.setFlags(self.ItemIsMovable | self.ItemIsSelectable | self.ItemSendsGeometryChanges)

        self.name = block_name
        self.uid = uid or block_name
        self.num_cases = num_cases
        self.outputs = {}

        self.label = QGraphicsTextItem(block_name, self)
        self.label.setDefaultTextColor(QColor("white"))
        self.label.setPos((width - self.label.boundingRect().width()) / 2, 5)
        self.is_highlighted = False
        self.outputs = {}
        self.create_output_blocks()

    def create_output_blocks(self):
        labels = [f"case_{i}" for i in range(self.num_cases)] + ["default"]
        font_metrics = QFontMetricsF(self.label.font())
        text_height = font_metrics.height()
        gap = text_height / 2
        y = self.label.boundingRect().height() + 10

        for label in labels:
            block = OutputSubBlockItem(label, self)
            block.setPos(10, y)
            self.outputs[label] = block
            if self.scene():
                self.scene().addItem(block)
            else:
                block.setParentItem(self)
            y += block.rect().height() + gap

        total_height = y
        self.setRect(0, 0, self.rect().width(), total_height)

    def set_highlighted(self, state):
        self.is_highlighted = state
        self.update()

    def paint(self, painter, option, widget=None):
        self.setPen(self.selected_pen if self.isSelected() else
                    self.highlight_pen if self.is_highlighted else
                    self.default_pen)
        super().paint(painter, option, widget)

    def itemChange(self, change, value):
        if change == self.ItemPositionChange and self.scene():
            for output in self.outputs.values():
                if output.output_arrow:
                    output.output_arrow._force_snap_start = True
                    output.output_arrow.update_path()
        return super().itemChange(change, value)


class WaypointItem(QGraphicsEllipseItem):
    def __init__(self, pos, arrow):
        super().__init__(-8, -8, 16, 16)
        self.setBrush(QBrush(QColor("yellow")))
        self.setFlags(self.ItemIsMovable | self.ItemIsSelectable)
        self.setZValue(1)
        self.setPos(pos)
        self.arrow = arrow

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        self.arrow.notify_waypoint_moved(self)
        self.arrow.update_path()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.ungrabMouse()

        index = self.arrow.waypoints.index(self)
        prev_wp = self.arrow.waypoints[index - 1] if index > 0 else None
        next_wp = self.arrow.waypoints[index + 1] if index + 1 < len(self.arrow.waypoints) else None

        def is_too_close(wp):
            return wp and (self.pos() - wp.pos()).manhattanLength() < 10

        # waypoint同士で重なったら削除
        if is_too_close(prev_wp) or is_too_close(next_wp):
            self.arrow.scene().removeItem(self)
            self.arrow.waypoints.remove(self)
            self.arrow.update_path()
            return

        # 始点に近ければ削除
        if index == 0 and (self.pos() - self.arrow.start_handle.pos()).manhattanLength() < 10:
            self.arrow.scene().removeItem(self)
            self.arrow.waypoints.remove(self)
            self.arrow.update_path()
            return

        # 終点に近ければ削除
        if index == len(self.arrow.waypoints) - 1 and (self.pos()
                                                       - self.arrow.end_handle.pos()).manhattanLength() < 10:
            self.arrow.scene().removeItem(self)
            self.arrow.waypoints.remove(self)
            self.arrow.update_path()
            return


class HoverPoint(QGraphicsEllipseItem):
    def __init__(self, pos, arrow, segment_index):
        super().__init__(-6, -6, 12, 12)
        self.setBrush(QBrush(QColor("white")))
        self.setZValue(0.5)
        self.setPos(pos)
        self.setAcceptHoverEvents(True)
        self.setFlag(self.ItemIsMovable, False)
        self.arrow = arrow
        self.segment_index = segment_index

    def mousePressEvent(self, event):
        waypoint = self.arrow.insert_waypoint(self.segment_index, self.scenePos())
        if self.scene():
            self.scene().removeItem(self)
        waypoint.setSelected(True)
        waypoint.grabMouse()
        waypoint.mousePressEvent(event)


class ArrowEndpointHandle(QGraphicsEllipseItem):
    def __init__(self, arrow, is_start):
        super().__init__(-8, -8, 16, 16)
        self.setBrush(QBrush(QColor("red" if is_start else "blue")))
        self.setFlags(self.ItemIsMovable | self.ItemIsSelectable)
        self.setZValue(2)
        self.arrow = arrow
        self.is_start = is_start
        self.is_dragging = False

    def mousePressEvent(self, event):
        self.is_dragging = True
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        for item in self.scene().items():
            if isinstance(item, FrameBlockItem):
                item.set_highlighted(item.sceneBoundingRect().contains(self.scenePos()))
        self.arrow.update_path()

    def mouseReleaseEvent(self, event):
        self.is_dragging = False
        if self.is_start:
            self.arrow._force_snap_start = True
        else:
            self.arrow._force_snap_end = True

        scene = self.scene()
        target = None
        for item in scene.items(self.scenePos()):
            if isinstance(item, FrameBlockItem):
                if self.is_start:
                    if item.output_arrow is not None and item.output_arrow != self.arrow:
                        target = None
                        break
                    item.output_arrow = self.arrow  # 出力は1本のみ
                else:
                    if self.arrow not in item.input_arrows:
                        item.input_arrows.append(self.arrow)  # 入力は何本でもOK
                target = item
                break

        if self.is_start:
            self.arrow.start_item = target
        else:
            self.arrow.end_item = target

        for item in scene.items():
            if hasattr(item, "set_highlighted"):
                item.set_highlighted(False)
        self.arrow.update_path()
        super().mouseReleaseEvent(event)


class ArrowItem(QGraphicsPathItem):
    def __init__(self, arrow_id):
        super().__init__()
        self.arrow_id = arrow_id
        self.setZValue(-1)
        self.start_item = None
        self.end_item = None
        self.start_handle = ArrowEndpointHandle(self, True)
        self.end_handle = ArrowEndpointHandle(self, False)
        self.waypoints = []
        self.hover_points = []
        self._recently_moved_waypoint = None
        self._force_snap_start = False
        self._force_snap_end = False
        self.start_handle.setPos(0, 0)
        self.end_handle.setPos(100, 0)

    def notify_waypoint_moved(self, waypoint):
        self._recently_moved_waypoint = waypoint

    def add_to_scene(self, scene):
        scene.addItem(self)
        scene.addItem(self.start_handle)
        scene.addItem(self.end_handle)

    def insert_waypoint(self, index, pos):
        wp = WaypointItem(pos, self)
        self.scene().addItem(wp)
        self.waypoints.insert(index, wp)
        self.notify_waypoint_moved(wp)
        self.update_path()
        return wp

    def remove_all_waypoints(self):
        for wp in self.waypoints:
            self.scene().removeItem(wp)
        self.waypoints.clear()

    def refresh_hover_points(self):
        for hp in self.hover_points:
            self.scene().removeItem(hp)
        self.hover_points.clear()

        points = [self.start_handle.pos()] + [wp.pos() for wp in self.waypoints] + [self.end_handle.pos()]
        for i in range(len(points) - 1):
            mid = (points[i] + points[i + 1]) * 0.5
            hp = HoverPoint(mid, self, i)
            self.scene().addItem(hp)
            self.hover_points.append(hp)

    def update_path(self):
        pen = QPen(QColor("white"), 4)
        is_connected = self.start_item is not None and self.end_item is not None
        pen.setStyle(Qt.SolidLine if is_connected else Qt.DashLine)
        self.setPen(pen)

        if self.start_item and (self._force_snap_start or (
                not self.start_handle.is_dragging and (
                    not self.waypoints or self._recently_moved_waypoint is self.waypoints[0]
                ))):
            neighbor = self.waypoints[0].pos() if self.waypoints else self.end_handle.pos()
            center = self.start_item.sceneBoundingRect().center()
            p1 = compute_edge_point(center, neighbor,
                                    self.start_item.rect().width(), self.start_item.rect().height())
            self.start_handle.setPos(p1)
        else:
            p1 = self.start_handle.pos()
        self._force_snap_start = False

        if self.end_item and (self._force_snap_end or (
                not self.end_handle.is_dragging and (
                    not self.waypoints or self._recently_moved_waypoint is self.waypoints[-1]
                ))):
            neighbor = self.waypoints[-1].pos() if self.waypoints else self.start_handle.pos()
            center = self.end_item.sceneBoundingRect().center()
            p2 = compute_edge_point(center, neighbor,
                                    self.end_item.rect().width(), self.end_item.rect().height())
            self.end_handle.setPos(p2)
        else:
            p2 = self.end_handle.pos()
        self._force_snap_end = False

        path = QPainterPath()
        path.moveTo(p1)
        for wp in self.waypoints:
            path.lineTo(wp.pos())
        path.lineTo(p2)

        if path.elementCount() >= 2:
            angle = math.atan2(p2.y() - path.elementAt(path.elementCount() - 2).y,
                               p2.x() - path.elementAt(path.elementCount() - 2).x)
            arrow_size = 24
            arrow_p1 = p2 - QPointF(arrow_size * math.cos(angle - math.pi / 6),
                                    arrow_size * math.sin(angle - math.pi / 6))
            arrow_p2 = p2 - QPointF(arrow_size * math.cos(angle + math.pi / 6),
                                    arrow_size * math.sin(angle + math.pi / 6))
            path.moveTo(p2)
            path.lineTo(arrow_p1)
            path.moveTo(p2)
            path.lineTo(arrow_p2)

        self.setPath(path)
        self.refresh_hover_points()
        self._recently_moved_waypoint = None


class MotionFlowScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundBrush(QColor("#111111"))
        self.block_counter = 0
        self.blocks = []
        self.arrow_counter = 0
        self.arrows = []

    def _generate_block_id(self, name):
        safe = "".join(c if c.isalnum() else "_" for c in name)
        uid = f"{safe}_id{self.block_counter:03}"
        self.block_counter += 1
        return uid

    def _generate_arrow_id(self):
        aid = f"arrow_{self.arrow_counter:03}"
        self.arrow_counter += 1
        return aid

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        name = event.mimeData().text()
        pos = event.scenePos()
        uid = self._generate_block_id(name)
        item = FrameBlockItem(name, uid=uid)
        item.setPos(pos)
        self.addItem(item)
        event.acceptProposedAction()

    def contextMenuEvent(self, event):
        item = self.itemAt(event.scenePos(), self.views()[0].transform())
        menu = QMenu()
        if isinstance(self, FrameBlockItem):
            delete_action = menu.addAction("Delete Frame Block")
            action = menu.exec_(event.screenPos())
            if action == delete_action:
                scene = self.scene()
                if scene:
                    scene.remove_block_and_arrows(self)
        elif isinstance(self, IfBlockItem):
            delete_action = menu.addAction("Delete If Block")
            action = menu.exec_(event.screenPos())
            if action == delete_action:
                scene = self.scene()
                if scene:
                    scene.remove_block_and_arrows(self)
        elif isinstance(self, SwitchBlockItem):
            delete_action = menu.addAction("Delete Switch Block")
            action = menu.exec_(event.screenPos())
            if action == delete_action:
                scene = self.scene()
                if scene:
                    scene.remove_block_and_arrows(self)
        elif isinstance(self, ArrowItem):
            delete_arrow_action = menu.addAction("Delete Arrow")
            action = menu.exec_(event.screenPos())
            if action == delete_arrow_action:
                scene = self.scene()
                if scene:
                    scene.remove_arrow(self)
        elif isinstance(self, OutputSubBlockItem):
            item.setSelected(True)
            item.contextMenuEvent(event)
        else:
            new_frame_action = QAction("New Frame", menu)
            new_if_action = QAction("New If", menu)
            new_switch_action = QAction("New Switch", menu)
            new_arrow_action = QAction("New Arrow", menu)

            menu.addAction(new_frame_action)
            menu.addAction(new_if_action)
            menu.addAction(new_switch_action)
            menu.addAction(new_arrow_action)

            selected_action = menu.exec_(event.screenPos())
            pos = event.scenePos()

            if selected_action == new_frame_action:
                block = FrameBlockItem(self._generate_block_id("frame"))
                block.setPos(pos)
                self.addItem(block)
                self.blocks.append(block)

            elif selected_action == new_if_action:
                block = IfBlockItem(self._generate_block_id("if"))
                block.setPos(pos)
                self.addItem(block)
                self.blocks.append(block)

            elif selected_action == new_switch_action:
                block = SwitchBlockItem(self._generate_block_id("switch"))
                block.setPos(pos)
                self.addItem(block)
                self.blocks.append(block)

            elif selected_action == new_arrow_action:
                arrow = ArrowItem(self._generate_arrow_id())
                arrow.start_handle.setPos(pos)
                arrow.end_handle.setPos(pos + QPointF(100, 0))
                arrow.add_to_scene(self)
                arrow.update_path()
                self.arrows.append(arrow)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            for item in self.selectedItems():
                if isinstance(item, WaypointItem):
                    arrow = item.arrow
                    arrow.waypoints.remove(item)
                    self.removeItem(item)
                    arrow.update_path()  # ← 線の再計算をここで実行！
                else:
                    self.removeItem(item)
        else:
            super().keyPressEvent(event)

    def save_layout_yaml(self):
        layout = {"block": {}, "arrow": {}}
        used_uids = set()
        items = [item for item in self.items() if isinstance(item, FrameBlockItem)]
        items.sort(key=lambda i: i.uid)

        for idx, item in enumerate(items):
            if not hasattr(item, 'uid') or not item.uid:
                item.uid = self._generate_block_id(item.name)
            while item.uid in used_uids:
                item.uid = self._generate_block_id(item.name)
            used_uids.add(item.uid)
            uid = item.uid
            layout["block"][uid] = {
                "info": {"type": "frame", "filename": item.name, "id": idx},
                "place": {"x": int(item.pos().x()), "y": int(item.pos().y())},
                "connection": {"output": {}}
            }

        # save arrows and waypoints
        for arrow in self.arrows:
            layout["arrow"][arrow.arrow_id] = {
                "info": {"id": int(arrow.arrow_id.split("_")[-1])},
                "waypoints": (
                    [[int(arrow.start_handle.pos().x()), int(arrow.start_handle.pos().y())]]
                    + [[int(wp.pos().x()), int(wp.pos().y())] for wp in arrow.waypoints]
                    + [[int(arrow.end_handle.pos().x()), int(arrow.end_handle.pos().y())]]
                )
            }

        # build output connection (with out_0, out_1, ...)
        arrow_outputs = {}
        for arrow in self.arrows:
            if arrow.start_item and arrow.end_item:
                sid = arrow.start_item.uid
                tid = arrow.end_item.uid
                block = layout["block"].get(sid)
                if block is not None:
                    output_conn = block["connection"]["output"]
                    idx = arrow_outputs.get(sid, 0)
                    out_key = f"out_{idx}"
                    output_conn[out_key] = {
                        "target": tid,
                        "ch": 0,
                        "arrow": arrow.arrow_id
                    }
                    arrow_outputs[sid] = idx + 1
        return layout

    def load_layout_yaml(self, layout):
        self.clear()
        self.arrows = []
        uid_to_item = {}

        # 1. ブロックを先に復元
        for uid, block in layout.get("block", {}).items():
            name = block["info"]["filename"]
            x = block["place"]["x"]
            y = block["place"]["y"]
            item = FrameBlockItem(name, uid=uid)
            item.setPos(x, y)
            if "connection" in block:
                item.connection = block["connection"]
            self.addItem(item)
            uid_to_item[uid] = item

        # 2. 矢印を作成（まずシーンに追加してから waypoint を復元）
        arrow_map = {}
        for arrow_id, arrow_data in layout.get("arrow", {}).items():
            arrow = ArrowItem(arrow_id)
            arrow.add_to_scene(self)  # ← 先に追加
            waypoints = arrow_data.get("waypoints", [])
            for idx, [x, y] in enumerate(waypoints):
                if idx == 0:
                    arrow.start_handle.setPos(QPointF(x, y))
                elif idx == len(waypoints) - 1:
                    arrow.end_handle.setPos(QPointF(x, y))
                else:
                    arrow.insert_waypoint(idx - 1, QPointF(x, y))
            arrow_map[arrow_id] = arrow

        # 3. block.connection.output から start/end を設定
        for uid, block in layout.get("block", {}).items():
            outputs = block.get("connection", {}).get("output", {})
            for out in outputs.values():
                arrow_id = out.get("arrow")
                target_uid = out.get("target")
                if arrow_id in arrow_map:
                    arrow = arrow_map[arrow_id]
                    arrow.start_item = uid_to_item.get(uid)
                    arrow.end_item = uid_to_item.get(target_uid)

        # 4. path 再描画 + リスト登録
        for arrow in arrow_map.values():
            arrow.update_path()
            self.arrows.append(arrow)
