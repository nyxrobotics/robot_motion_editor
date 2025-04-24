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
            for item in self.scene().items():
                if isinstance(item, ArrowItem) and (item.start_item == self or item.end_item == self):
                    item.update_path()
        return super().itemChange(change, value)


class WaypointItem(QGraphicsEllipseItem):
    def __init__(self, pos, arrow):
        super().__init__(-4, -4, 8, 8)
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

        # 隣接する前後の waypoint を取得
        prev_wp = self.arrow.waypoints[index - 1] if index > 0 else None
        next_wp = self.arrow.waypoints[index + 1] if index + 1 < len(self.arrow.waypoints) else None

        def is_too_close(wp):
            return wp and (self.pos() - wp.pos()).manhattanLength() < 10  # 距離が10以下なら重なりと見なす

        if is_too_close(prev_wp) or is_too_close(next_wp):
            self.arrow.scene().removeItem(self)
            self.arrow.waypoints.remove(self)
            self.arrow.update_path()


class HoverPoint(QGraphicsEllipseItem):
    def __init__(self, pos, arrow, segment_index):
        super().__init__(-5, -5, 10, 10)
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
        super().__init__(-6, -6, 12, 12)
        self.setBrush(QBrush(QColor("red" if is_start else "blue")))
        self.setFlags(self.ItemIsMovable | self.ItemIsSelectable)
        self.setZValue(2)
        self.arrow = arrow
        self.is_start = is_start
        self.is_dragging = False  # ← 追加

    def mousePressEvent(self, event):
        self.is_dragging = True  # ← 開始
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        pos = self.scenePos()
        for item in self.scene().items():
            if isinstance(item, FrameBlockItem):
                item.set_highlighted(item.sceneBoundingRect().contains(pos))
        self.arrow.update_path()

    def mouseReleaseEvent(self, event):
        self.is_dragging = False  # ← 終了
        scene = self.scene()
        target = None
        for item in scene.items(self.scenePos()):
            if isinstance(item, FrameBlockItem):
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
        self.setPen(QPen(QColor("white"), 4))
        self.setZValue(-1)
        self.arrow_id = arrow_id
        self.start_item = None
        self.end_item = None
        self.start_handle = ArrowEndpointHandle(self, True)
        self.end_handle = ArrowEndpointHandle(self, False)
        self.waypoints = []
        self.hover_points = []
        self._recently_moved_waypoint = None
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

        points = [self.start_handle.pos()] + \
                 [wp.pos() for wp in self.waypoints] + \
                 [self.end_handle.pos()]
        for i in range(len(points) - 1):
            mid = (points[i] + points[i + 1]) * 0.5
            hp = HoverPoint(mid, self, i)
            self.scene().addItem(hp)
            self.hover_points.append(hp)

    def update_path(self):
        # --- p1 ---
        if self.start_item and not self.start_handle.is_dragging:
            update = not self.waypoints or self._recently_moved_waypoint is self.waypoints[0]
            if update:
                neighbor = self.waypoints[0].pos() if self.waypoints else self.end_handle.pos()
                center = self.start_item.sceneBoundingRect().center()
                p1 = compute_edge_point(center, neighbor,
                                        self.start_item.rect().width(), self.start_item.rect().height())
                self.start_handle.setPos(p1)
        p1 = self.start_handle.pos()

        # --- p2 ---
        if self.end_item and not self.end_handle.is_dragging:
            update = not self.waypoints or self._recently_moved_waypoint is self.waypoints[-1]
            if update:
                neighbor = self.waypoints[-1].pos() if self.waypoints else self.start_handle.pos()
                center = self.end_item.sceneBoundingRect().center()
                p2 = compute_edge_point(center, neighbor,
                                        self.end_item.rect().width(), self.end_item.rect().height())
                self.end_handle.setPos(p2)
        p2 = self.end_handle.pos()

        path = QPainterPath()
        path.moveTo(p1)
        for wp in self.waypoints:
            path.lineTo(wp.pos())  # ← scenePos ではなく pos
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
        self.id_counter = 0
        self.arrow_counter = 0
        self.arrows = []

    def _generate_uid(self, name):
        safe = "".join(c if c.isalnum() else "_" for c in name)
        uid = f"frame_{safe}_id{self.id_counter:03}"
        self.id_counter += 1
        return uid

    def _generate_arrow_id(self):
        aid = f"arrow_{self.arrow_counter:03}"
        self.arrow_counter += 1
        return aid

    def contextMenuEvent(self, event):
        item = self.itemAt(event.scenePos(), self.views()[0].transform())
        menu = QMenu()
        if isinstance(item, FrameBlockItem):
            item.setSelected(True)
            item.contextMenuEvent(event)
        else:
            menu.addAction(QAction("Add New Frame", menu))
            arrow_action = QAction("New Arrow", menu)
            menu.addAction(arrow_action)
            selected_action = menu.exec_(event.screenPos())
            if selected_action == arrow_action:
                arrow = ArrowItem(self._generate_arrow_id())
                pos = event.scenePos()
                arrow.start_handle.setPos(pos)
                arrow.end_handle.setPos(pos + QPointF(100, 0))
                arrow.add_to_scene(self)
                arrow.update_path()
                self.arrows.append(arrow)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            for item in self.selectedItems():
                if isinstance(item, WaypointItem):
                    item.arrow.waypoints.remove(item)
                self.removeItem(item)
        else:
            super().keyPressEvent(event)

    def to_layout_dict(self):
        layout = {"block": {}, "arrow": {}}
        used_uids = set()
        items = [item for item in self.items() if isinstance(item, FrameBlockItem)]
        items.sort(key=lambda i: i.uid)
        for idx, item in enumerate(items):
            if not hasattr(item, 'uid') or not item.uid:
                item.uid = self._generate_uid(item.name)
            while item.uid in used_uids:
                item.uid = self._generate_uid(item.name)
            used_uids.add(item.uid)
            uid = item.uid
            layout["block"][uid] = {
                "info": {"type": "frame", "filename": item.name, "id": idx},
                "place": {"x": int(item.pos().x()), "y": int(item.pos().y())},
                "connection": item.connection if hasattr(item, "connection") else {"output": {}}
            }
        for arrow in self.arrows:
            if arrow.start_item and arrow.end_item:
                layout["arrow"][arrow.arrow_id] = {
                    "info": {"id": int(arrow.arrow_id.split("_")[-1])},
                    "waypoints": []
                }
        return layout

    def load_layout_dict(self, layout):
        self.clear()
        self.arrows = []
        for uid, block in layout.get("block", {}).items():
            name = block["info"]["filename"]
            x = block["place"]["x"]
            y = block["place"]["y"]
            item = FrameBlockItem(name, uid=uid)
            item.setPos(x, y)
            if "connection" in block:
                item.connection = block["connection"]
            self.addItem(item)
