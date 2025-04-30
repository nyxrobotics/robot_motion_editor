import math
import os

import yaml
from PyQt5.QtCore import QPointF
from PyQt5.QtCore import QRectF
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
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtWidgets import QMenu
from PyQt5.QtWidgets import QMessageBox

from ..logic.frame_file_manager import create_default_frame
from ..logic.frame_file_manager import save_frame_file
from ..logic.if_condition_file_manager import save_if_condition
from ..logic.switch_condition_file_manager import save_switch_condition


def compute_edge_point(center, target, width, height):
    dx = target.x() - center.x()
    dy = target.y() - center.y()
    if dx == 0 and dy == 0:
        return center
    scale = 0.5 / max(abs(dx) / width, abs(dy) / height)
    return QPointF(center.x() + dx * scale, center.y() + dy * scale)


class FrameBlockItem(QGraphicsRectItem):
    def __init__(self, id, filename):
        self.type = "frame"
        self.id = id
        self.filename = filename
        self.name = f"{self.type}_{self.id}_{self.filename}"
        self.max_inputs = -1
        self.max_outputs = 1
        self.input_arrows = []
        self.output_arrows = []

        label_text = QGraphicsTextItem(self.name)
        font_metrics = QFontMetricsF(label_text.font())
        text_width = font_metrics.width(self.name)
        width = max(120, text_width + 20)
        height = 60

        super().__init__(0, 0, width, height)
        self.setBrush(QBrush(QColor("#1a1a1a")))
        self.default_pen = QPen(QColor("#ffffff"), 3)
        self.highlight_pen = QPen(QColor("#00ff00"), 3)
        self.selected_pen = QPen(QColor("#00ffff"), 4)
        self.setPen(self.default_pen)
        self.setFlags(self.ItemIsMovable | self.ItemIsSelectable | self.ItemSendsGeometryChanges)

        self.label = QGraphicsTextItem(self.name, self)
        self.label.setDefaultTextColor(QColor("white"))
        self.label.setPos(
            (width - self.label.boundingRect().width()) / 2,
            (height - self.label.boundingRect().height()) / 2
        )
        self.is_highlighted = False

    def can_accept_input(self):
        return self.max_inputs == -1 or len(self.input_arrows) < self.max_inputs

    def can_accept_output(self):
        return self.max_outputs == -1 or len(self.output_arrows) < self.max_outputs

    def set_highlighted(self, state):
        self.is_highlighted = state
        self.update()

    def paint(self, painter, option, widget=None):
        if self.isSelected():
            self.setPen(self.selected_pen)
        elif self.is_highlighted:
            self.setPen(self.highlight_pen)
        else:
            self.setPen(self.default_pen)
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

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self.scene():
            for item in self.scene().items():
                if isinstance(item, ArrowItem):
                    item._force_snap_start = True
                    item._force_snap_end = True
                    item.update_path()

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self.scene().editor_widget.open_frame_editor(self.filename)

    def remove_from_scene(self):
        scene = self.scene()
        if scene:
            # Remove all input arrows
            for arrow in list(self.input_arrows):
                if arrow.start_item and arrow in arrow.start_item.output_arrows:
                    arrow.start_item.output_arrows.remove(arrow)
                if arrow.end_item and arrow in arrow.end_item.input_arrows:
                    arrow.end_item.input_arrows.remove(arrow)
                arrow.remove_from_scene()
            self.input_arrows.clear()
            # Remove all output arrows
            for arrow in list(self.output_arrows):
                if arrow.start_item and arrow in arrow.start_item.output_arrows:
                    arrow.start_item.output_arrows.remove(arrow)
                if arrow.end_item and arrow in arrow.end_item.input_arrows:
                    arrow.end_item.input_arrows.remove(arrow)
                arrow.remove_from_scene()
            self.output_arrows.clear()
            # Remove self from scene
            scene.removeItem(self)


class OutputSubBlockItem(QGraphicsRectItem):
    def __init__(self, label, parent_block):
        # Label text (e.g. "True", "False", "case_0")
        self.name = label
        # Maximum number of input/output arrows
        self.max_inputs = 0
        self.max_outputs = 1

        # Lists to store connected arrows
        self.input_arrows = []
        self.output_arrows = []

        # Reference to parent block (IfBlockItem or SwitchBlockItem)
        self.parent_block = parent_block

        self.label = label

        # Calculate size based on label text
        font_metrics = QFontMetricsF(QGraphicsTextItem(label).font())
        text_width = font_metrics.width(label)
        text_height = font_metrics.height()
        width = max(100, text_width + 20)
        height = max(30, text_height + 10)

        super().__init__(0, 0, width, height)

        # Appearance settings
        self.setBrush(QBrush(QColor("#2b2b2b")))
        self.default_pen = QPen(QColor("#aaaaaa"), 2)
        self.highlight_pen = QPen(QColor("#00ff00"), 3)
        self.selected_pen = QPen(QColor("#00ffff"), 3)
        self.setPen(self.default_pen)

        self.setFlags(self.ItemIsSelectable | self.ItemSendsGeometryChanges)

        # Display label centered in block
        self.label_item = QGraphicsTextItem(label, self)
        self.label_item.setDefaultTextColor(QColor("white"))
        self.label_item.setPos(
            (width - self.label_item.boundingRect().width()) / 2,
            (height - self.label_item.boundingRect().height()) / 2
        )
        self.is_highlighted = False

    def can_accept_input(self):
        # Returns True if more input arrows can be accepted
        return self.max_inputs == -1 or len(self.input_arrows) < self.max_inputs

    def can_accept_output(self):
        # Returns True if more output arrows can be accepted
        return self.max_outputs == -1 or len(self.output_arrows) < self.max_outputs

    def set_highlighted(self, state):
        # Set highlight state and update appearance
        self.is_highlighted = state
        self.update()

    def paint(self, painter, option, widget=None):
        # Set pen based on selection/highlight state
        if self.isSelected():
            self.setPen(self.selected_pen)
        elif self.is_highlighted:
            self.setPen(self.highlight_pen)
        else:
            self.setPen(self.default_pen)
        super().paint(painter, option, widget)

    def itemChange(self, change, value):
        # Update connected arrows when position changes
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

    def mouseReleaseEvent(self, event):
        # Update connected arrows after moving
        super().mouseReleaseEvent(event)
        if self.scene():
            for item in self.scene().items():
                if isinstance(item, ArrowItem):
                    item._force_snap_start = True
                    item._force_snap_end = True
                    item.update_path()

    def on_parent_moved(self):
        # Called when parent block moves; update connected arrows
        for arrow in self.output_arrows:
            arrow._force_snap_start = True
            arrow.update_path()

    def remove_from_scene(self):
        scene = self.scene()
        if scene:
            # Remove all input arrows
            for arrow in list(self.input_arrows):
                if arrow.start_item and arrow in arrow.start_item.output_arrows:
                    arrow.start_item.output_arrows.remove(arrow)
                if arrow.end_item and arrow in arrow.end_item.input_arrows:
                    arrow.end_item.input_arrows.remove(arrow)
                arrow.remove_from_scene()
            self.input_arrows.clear()

            # Remove all output arrows
            for arrow in list(self.output_arrows):
                if arrow.start_item and arrow in arrow.start_item.output_arrows:
                    arrow.start_item.output_arrows.remove(arrow)
                if arrow.end_item and arrow in arrow.end_item.input_arrows:
                    arrow.end_item.input_arrows.remove(arrow)
                arrow.remove_from_scene()
            self.output_arrows.clear()

            # Remove self from scene
            scene.removeItem(self)


class IfBlockItem(QGraphicsRectItem):
    def __init__(self, id, filename):

        self.type = "if"
        self.id = id
        self.filename = filename
        self.name = f"{self.type}_{self.id}_{self.filename}"

        self.max_inputs = -1
        self.max_outputs = 0
        self.input_arrows = []
        self.output_arrows = []
        self.output_sub_blocks = {}

        label_text = QGraphicsTextItem(self.name)
        font_metrics = QFontMetricsF(label_text.font())
        text_width = font_metrics.width(self.name)
        width = max(120, text_width + 20)
        super().__init__(0, 0, width, 60)
        self.setBrush(QBrush(QColor("#1a1a1a")))
        self.default_pen = QPen(QColor("#ffffff"), 3)
        self.highlight_pen = QPen(QColor("#00ff00"), 3)
        self.selected_pen = QPen(QColor("#00ffff"), 4)
        self.setPen(self.default_pen)
        self.setFlags(self.ItemIsMovable | self.ItemIsSelectable | self.ItemSendsGeometryChanges)

        self.label = QGraphicsTextItem(self.name, self)
        self.label.setDefaultTextColor(QColor("white"))
        self.label.setPos((width - self.label.boundingRect().width()) / 2, 5)
        self.is_highlighted = False
        self.create_output_blocks()

    def create_output_blocks(self):
        output_sub_labels = ["True", "False"]
        font_metrics = QFontMetricsF(self.label.font())
        text_height = font_metrics.height()
        gap = text_height / 2
        y = self.label.boundingRect().height() + 10

        # Outputブロックをまず仮作成して幅を測定
        output_blocks = []
        max_width = 0
        for out_label in output_sub_labels:
            block = OutputSubBlockItem(out_label, self)
            output_blocks.append(block)
            max_width = max(max_width, block.rect().width())

        # If本体の幅を必要に応じて広げる
        min_required_width = max_width + 2 * gap
        if self.rect().width() < min_required_width:
            self.setRect(0, 0, min_required_width, self.rect().height())

        # Outputブロックを中央揃えで配置
        for block in output_blocks:
            block.setParentItem(self)
            block_x = (self.rect().width() - block.rect().width()) / 2
            block.setPos(block_x, y)
            self.output_sub_blocks[block.name] = block
            y += block.rect().height() + gap

        # 全体の高さを更新
        total_height = y
        self.setRect(0, 0, self.rect().width(), total_height)

    def can_accept_input(self):
        return self.max_inputs == -1 or len(self.input_arrows) < self.max_inputs

    def can_accept_output(self):
        return self.max_outputs == -1 or len(self.output_arrows) < self.max_outputs

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
            for subblock in getattr(self, 'output_sub_blocks', {}).values():
                if hasattr(subblock, "on_parent_moved"):
                    subblock.on_parent_moved()
        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self.scene():
            for item in self.scene().items():
                if isinstance(item, ArrowItem):
                    item._force_snap_start = True
                    item._force_snap_end = True
                    item.update_path()
            for subblock in getattr(self, 'output_sub_blocks', {}).values():
                if hasattr(subblock, "on_parent_moved"):
                    subblock.on_parent_moved()

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self.scene().editor_widget.open_if_condition_editor(self.filename)

    def remove_from_scene(self):
        scene = self.scene()
        if scene:
            # 入力矢印を全て除去
            for arrow in list(self.input_arrows):
                if arrow.start_item and arrow in arrow.start_item.output_arrows:
                    arrow.start_item.output_arrows.remove(arrow)
                if arrow.end_item and arrow in arrow.end_item.input_arrows:
                    arrow.end_item.input_arrows.remove(arrow)
                arrow.remove_from_scene()
            self.input_arrows.clear()

            # 出力矢印も全て除去
            for arrow in list(self.output_arrows):
                if arrow.start_item and arrow in arrow.start_item.output_arrows:
                    arrow.start_item.output_arrows.remove(arrow)
                if arrow.end_item and arrow in arrow.end_item.input_arrows:
                    arrow.end_item.input_arrows.remove(arrow)
                arrow.remove_from_scene()
            self.output_arrows.clear()

            # 自分をシーンから削除
            scene.removeItem(self)


class SwitchBlockItem(QGraphicsRectItem):
    def __init__(self, id, filename, num_cases=3):

        self.type = "switch"
        self.id = id
        self.filename = filename
        self.name = f"{self.type}_{self.id}_{self.filename}"
        self.num_cases = num_cases

        self.max_inputs = -1
        self.max_outputs = 0
        self.input_arrows = []
        self.output_arrows = []
        self.output_sub_blocks = {}

        label_text = QGraphicsTextItem(self.name)
        font_metrics = QFontMetricsF(label_text.font())
        text_width = font_metrics.width(self.name)
        width = max(120, text_width + 20)
        super().__init__(0, 0, width, 60)
        self.setBrush(QBrush(QColor("#1a1a1a")))
        self.default_pen = QPen(QColor("#ffffff"), 3)
        self.highlight_pen = QPen(QColor("#00ff00"), 3)
        self.selected_pen = QPen(QColor("#00ffff"), 4)
        self.setPen(self.default_pen)
        self.setFlags(self.ItemIsMovable | self.ItemIsSelectable | self.ItemSendsGeometryChanges)

        self.label = QGraphicsTextItem(self.name, self)
        self.label.setDefaultTextColor(QColor("white"))
        self.label.setPos((width - self.label.boundingRect().width()) / 2, 5)
        self.is_highlighted = False
        self.create_output_blocks()

    def create_output_blocks(self):
        output_sub_labels = ["default"] + [f"case_{i}" for i in range(self.num_cases - 1)]
        font_metrics = QFontMetricsF(self.label.font())
        text_height = font_metrics.height()
        gap = text_height / 2
        y = self.label.boundingRect().height() + 10

        output_blocks = []
        max_width = 0
        for out_label in output_sub_labels:
            block = OutputSubBlockItem(out_label, self)
            output_blocks.append(block)
            max_width = max(max_width, block.rect().width())

        min_required_width = max_width + 2 * gap
        if self.rect().width() < min_required_width:
            self.setRect(0, 0, min_required_width, self.rect().height())

        for block in output_blocks:
            block.setParentItem(self)
            block_x = (self.rect().width() - block.rect().width()) / 2
            block.setPos(block_x, y)
            self.output_sub_blocks[block.name] = block
            y += block.rect().height() + gap

        total_height = y
        self.setRect(0, 0, self.rect().width(), total_height)

    def can_accept_input(self):
        return self.max_inputs == -1 or len(self.input_arrows) < self.max_inputs

    def can_accept_output(self):
        return self.max_outputs == -1 or len(self.output_arrows) < self.max_outputs

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
            for subblock in getattr(self, 'output_sub_blocks', {}).values():
                if hasattr(subblock, "on_parent_moved"):
                    subblock.on_parent_moved()
        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self.scene():
            for item in self.scene().items():
                if isinstance(item, ArrowItem):
                    item._force_snap_start = True
                    item._force_snap_end = True
                    item.update_path()
            for subblock in getattr(self, 'output_sub_blocks', {}).values():
                if hasattr(subblock, "on_parent_moved"):
                    subblock.on_parent_moved()

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self.scene().editor_widget.open_switch_condition_editor(self.filename)

    def remove_from_scene(self):
        scene = self.scene()
        if scene:
            # 入力矢印を全て除去
            for arrow in list(self.input_arrows):
                if arrow.start_item and arrow in arrow.start_item.output_arrows:
                    arrow.start_item.output_arrows.remove(arrow)
                if arrow.end_item and arrow in arrow.end_item.input_arrows:
                    arrow.end_item.input_arrows.remove(arrow)
                arrow.remove_from_scene()
            self.input_arrows.clear()

            # 出力矢印も全て除去
            for arrow in list(self.output_arrows):
                if arrow.start_item and arrow in arrow.start_item.output_arrows:
                    arrow.start_item.output_arrows.remove(arrow)
                if arrow.end_item and arrow in arrow.end_item.input_arrows:
                    arrow.end_item.input_arrows.remove(arrow)
                arrow.remove_from_scene()
            self.output_arrows.clear()

            # 自分をシーンから削除
            scene.removeItem(self)


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

    def remove_from_scene(self):
        if self.arrow and self in self.arrow.waypoints:
            self.arrow.waypoints.remove(self)
        if self.scene():
            self.scene().removeItem(self)
        self.arrow.update_path()


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
            if isinstance(item, (FrameBlockItem, IfBlockItem, SwitchBlockItem, OutputSubBlockItem)):
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
            if isinstance(item, (FrameBlockItem, IfBlockItem, SwitchBlockItem, OutputSubBlockItem)):
                if self.is_start:
                    if item.max_outputs != -1 and len(item.output_arrows) >= item.max_outputs:
                        target = None
                        break
                    item.output_arrows.append(self.arrow)
                else:
                    if item.max_inputs != -1 and len(item.input_arrows) >= item.max_inputs:
                        target = None
                        break
                    item.input_arrows.append(self.arrow)
                target = item
                break

        if self.is_start:
            # もし前のstart_itemがあったら外す
            if self.arrow.start_item and self.arrow in self.arrow.start_item.output_arrows:
                self.arrow.start_item.output_arrows.remove(self.arrow)
            self.arrow.start_item = target
        else:
            # もし前のend_itemがあったら外す
            if self.arrow.end_item and self.arrow in self.arrow.end_item.input_arrows:
                self.arrow.end_item.input_arrows.remove(self.arrow)
            self.arrow.end_item = target

        for item in scene.items():
            if hasattr(item, "set_highlighted"):
                item.set_highlighted(False)
        self.arrow.update_path()
        super().mouseReleaseEvent(event)


class ArrowItem(QGraphicsPathItem):
    def __init__(self, id):
        super().__init__()

        self.type = "arrow"
        self.id = id
        self.name = f"{self.type}_{id}"

        self.setZValue(10)
        self.start_item = None
        self.end_item = None
        self.start_handle = ArrowEndpointHandle(self, True)
        self.end_handle = ArrowEndpointHandle(self, False)
        self.waypoints = []
        self.hover_points = []
        self._recently_moved_waypoint = None
        self._force_snap_start = False
        self._force_snap_end = False
        self.start_handle.setParentItem(self)
        self.end_handle.setParentItem(self)
        self.default_pen = QPen(QColor("#ffffff"), 3)
        self.highlight_pen = QPen(QColor("#00ff00"), 3)
        self.selected_pen = QPen(QColor("#00ffff"), 4)
        self.setPen(self.default_pen)
        self.setFlags(self.ItemIsSelectable)

    def notify_waypoint_moved(self, waypoint):
        self._recently_moved_waypoint = waypoint

    def add_to_scene(self, scene):
        scene.addItem(self)

    def insert_waypoint(self, index, pos):
        wp = WaypointItem(pos, self)
        wp.setParentItem(self)
        self.waypoints.insert(index, wp)
        self.notify_waypoint_moved(wp)
        self.update_path()
        return wp

    def remove_all_waypoints(self):
        for wp in self.waypoints:
            wp.setParentItem(None)  # 明示的に切り離す（念のため）
            if wp.scene():
                wp.scene().removeItem(wp)
        self.waypoints.clear()

    def refresh_hover_points(self):
        for hp in self.hover_points:
            hp.setParentItem(None)
            if hp.scene():
                hp.scene().removeItem(hp)
        self.hover_points.clear()

        points = [self.start_handle.pos()] + [wp.pos() for wp in self.waypoints] + [self.end_handle.pos()]
        for i in range(len(points) - 1):
            mid = (points[i] + points[i + 1]) * 0.5
            hp = HoverPoint(mid, self, i)
            hp.setParentItem(self)
            self.hover_points.append(hp)

    def update_path(self):
        pen = self.selected_pen if self.isSelected() else self.default_pen
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

    def remove_from_scene(self):
        if self.scene():
            print(f"[DEBUG] Removing ArrowItem: {self.name}")

            # start_item から自分を外す
            if self.start_item:
                if self in self.start_item.output_arrows:
                    print(f"[DEBUG] Removing from start_item.output_arrows: {self.start_item.name}")
                    self.start_item.output_arrows.remove(self)
                else:
                    print(f"[DEBUG] self not in start_item.output_arrows")

            # end_item から自分を外す
            if self.end_item:
                if self in self.end_item.input_arrows:
                    print(f"[DEBUG] Removing from end_item.input_arrows: {self.end_item.name}")
                    self.end_item.input_arrows.remove(self)
                else:
                    print(f"[DEBUG] self not in end_item.input_arrows")

            # Waypoints を消す
            for wp in self.waypoints:
                if self.scene().items().count(wp):
                    print(f"[DEBUG] Removing waypoint at {wp.pos()}")
                    self.scene().removeItem(wp)
            self.waypoints.clear()

            # HoverPoints を消す
            for hp in self.hover_points:
                if self.scene().items().count(hp):
                    print(f"[DEBUG] Removing hover point at {hp.pos()}")
                    self.scene().removeItem(hp)
            self.hover_points.clear()

            # ハンドルを消す
            if self.start_handle:
                print(f"[DEBUG] Removing start_handle")
                self.scene().removeItem(self.start_handle)
            if self.end_handle:
                print(f"[DEBUG] Removing end_handle")
                self.scene().removeItem(self.end_handle)

            # 最後に自分自身
            print(f"[DEBUG] Removing self ArrowItem")
            self.scene().removeItem(self)


class MotionFlowScene(QGraphicsScene):
    def __init__(self, editor_widget, parent=None):
        super().__init__(parent)
        self.editor_widget = editor_widget
        self.setBackgroundBrush(QColor("#111111"))
        self.block_objects = {}
        self.arrow_objects = {}
        self.setSceneRect(0, 0, 1000, 1000)

    def _generate_block_id(self):
        used_ids = {block.id for block in self.block_objects.values()}
        i = 0
        while i in used_ids:
            i += 1
        return i

    def _generate_arrow_id(self):
        used_ids = {arrow.id for arrow in self.arrow_objects.values()}
        i = 0
        while i in used_ids:
            i += 1
        return i

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        data = event.mimeData().text()
        if ":" not in data:
            event.ignore()
            return

        item_type, name = data.split(":", 1)
        id = self._generate_block_id()
        pos = event.scenePos()

        if item_type == "frame":
            item = FrameBlockItem(id, name)
        elif item_type == "if":
            item = IfBlockItem(id, name)
        elif item_type == "switch":
            # switchのcase数をyamlから取得して反映（オプション）
            switch_path = os.path.join(
                self.editor_widget.animation_root,
                self.editor_widget.current_animation_name,
                "conditions", "switch", f"{name}.yaml"
            )
            if os.path.exists(switch_path):
                with open(switch_path, "r") as f:
                    switch_data = yaml.safe_load(f)
                    num_cases = len(switch_data.get("case", [])) + 1  # default含む
            else:
                num_cases = 2
            item = SwitchBlockItem(id, name, num_cases=num_cases)
        else:
            event.ignore()
            return

        item.setPos(pos)
        self.addItem(item)
        self.block_objects[item.name] = item
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
                name, ok = QInputDialog.getText(None, "New Frame", "Enter frame name:")
                if ok and name.strip():
                    name = name.strip()
                    frames_dir = os.path.join(
                        self.editor_widget.animation_root,
                        self.editor_widget.current_animation_name,
                        "frames")
                    frame_path = os.path.join(frames_dir, f"{name}.yaml")

                    if os.path.exists(frame_path):
                        QMessageBox.warning(None, "Name Conflict", f"Frame '{name}' already exists.")
                        return

                    os.makedirs(frames_dir, exist_ok=True)
                    default_frame_data = create_default_frame()
                    save_frame_file(frame_path, default_frame_data)

                    id = self._generate_block_id()
                    block = FrameBlockItem(id, name)
                    block.setPos(pos)
                    self.addItem(block)
                    self.block_objects[block.name] = block

                    self.editor_widget.load_animation_list()

            elif selected_action == new_if_action:
                name, ok = QInputDialog.getText(None, "New If Condition", "Enter condition name:")
                if ok and name.strip():
                    name = name.strip()
                    conditions_dir = os.path.join(
                        self.editor_widget.animation_root,
                        self.editor_widget.current_animation_name,
                        "conditions",
                        "if")
                    condition_path = os.path.join(conditions_dir, f"{name}.yaml")

                    if os.path.exists(condition_path):
                        QMessageBox.warning(None, "Name Conflict", f"If condition '{name}' already exists.")
                        return

                    os.makedirs(conditions_dir, exist_ok=True)
                    default_if_data = {"expression": "", "condition": ""}
                    save_if_condition(
                        self.editor_widget.animation_root,
                        self.editor_widget.current_animation_name,
                        name,
                        default_if_data)

                    id = self._generate_block_id()
                    block = IfBlockItem(id, name)
                    block.setPos(pos)
                    self.addItem(block)
                    self.block_objects[block.name] = block

                    self.editor_widget.load_animation_list()

            elif selected_action == new_switch_action:
                name, ok = QInputDialog.getText(None, "New Switch Condition", "Enter condition name:")
                if ok and name.strip():
                    name = name.strip()
                    conditions_dir = os.path.join(
                        self.editor_widget.animation_root,
                        self.editor_widget.current_animation_name,
                        "conditions",
                        "switch")
                    condition_path = os.path.join(conditions_dir, f"{name}.yaml")

                    if os.path.exists(condition_path):
                        QMessageBox.warning(None, "Name Conflict", f"Switch condition '{name}' already exists.")
                        return

                    os.makedirs(conditions_dir, exist_ok=True)
                    default_switch_data = {"expression": "", "condition": "", "case": [0]}
                    save_switch_condition(
                        self.editor_widget.animation_root,
                        self.editor_widget.current_animation_name,
                        name,
                        default_switch_data)

                    id = self._generate_block_id()
                    block = SwitchBlockItem(id, name, num_cases=2)
                    block.setPos(pos)
                    self.addItem(block)
                    self.block_objects[block.name] = block

                    self.editor_widget.load_animation_list()
            elif selected_action == new_arrow_action:
                id = self._generate_arrow_id()
                arrow = ArrowItem(id)
                arrow.start_handle.setPos(pos)
                arrow.end_handle.setPos(pos + QPointF(100, 0))
                arrow.add_to_scene(self)
                arrow.update_path()
                self.arrow_objects[arrow.name] = arrow

    def remove_block_and_arrows(self, block):
        for arrow in list(getattr(block, 'input_arrows', [])):
            arrow.remove_from_scene()
            if arrow.name in self.arrow_objects:
                self.arrow_objects.pop(arrow.name)
        for arrow in list(getattr(block, 'output_arrows', [])):
            arrow.remove_from_scene()
            if arrow.name in self.arrow_objects:
                self.arrow_objects.pop(arrow.name)
        block.remove_from_scene()
        if block.name in self.block_objects:
            self.block_objects.pop(block.name)

    def remove_block(self, block):
        block.remove_from_scene()
        if block.name in self.block_objects:
            self.block_objects.pop(block.name)

    def remove_arrow(self, arrow):
        arrow.remove_from_scene()
        if arrow in self.arrow_objects:
            self.arrow_objects.pop(arrow.name)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            for item in self.selectedItems():
                if isinstance(item, (FrameBlockItem, IfBlockItem, SwitchBlockItem)):
                    self.remove_block(item)
                elif isinstance(item, (ArrowItem)):
                    self.remove_arrow(item)
                else:
                    return
        else:
            super().keyPressEvent(event)

    def compute_scene_rect(self):
        """Sceneに存在する全アイテムを囲う最小矩形を計算して返す"""
        items = self.items()
        if not items:
            return QRectF(0, 0, 1000, 1000)  # 初期サイズ（広めにしておく）

        bounding_rect = None
        for item in items:
            if not item.isVisible():
                continue
            rect = item.sceneBoundingRect()
            if bounding_rect is None:
                bounding_rect = rect
            else:
                bounding_rect = bounding_rect.united(rect)

        # 50ピクセルのマージンを追加
        if bounding_rect:
            margin = 100
            bounding_rect.adjust(-margin, -margin, margin, margin)
            return bounding_rect
        else:
            return QRectF(0, 0, 1000, 1000)

    def update_scene_rect(self):
        """シーン全体を囲うためのsceneRectを自動設定する"""
        rect = self.compute_scene_rect()
        self.setSceneRect(rect)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        # ドロップした直後にもsceneRectを更新
        self.update_scene_rect()

    def save_layout_yaml(self):
        layout = {"block": {}, "arrow": {}}

        for item in self.items():
            if isinstance(item, (FrameBlockItem, IfBlockItem, SwitchBlockItem)):
                block_data = {
                    "info": {
                        "type": item.type,
                        "filename": item.filename,
                        "id": item.id,
                    },
                    "place": {
                        "x": item.pos().x(),
                        "y": item.pos().y(),
                    },
                    "connection": {
                        "output": {}
                    }
                }

                # 出力ピンの全リストを取得
                output_labels = []
                if isinstance(item, FrameBlockItem):
                    output_labels = ["out_0"]
                elif isinstance(item, (IfBlockItem, SwitchBlockItem)):
                    output_labels = list(item.output_sub_blocks.keys())

                # 全出力ピンを保存（接続有無に関わらず）
                for label in output_labels:
                    subblock = item.output_sub_blocks.get(label) if hasattr(item, 'output_sub_blocks') else item
                    connection_data = {"ch": output_labels.index(label)}

                    if subblock.output_arrows:
                        arrow = subblock.output_arrows[0]
                        if arrow.end_item:
                            connection_data.update({
                                "target": arrow.end_item.name,
                                "arrow": arrow.name
                            })

                    block_data["connection"]["output"][label] = connection_data

                layout["block"][item.name] = block_data

            elif isinstance(item, ArrowItem):
                # 既存の矢印保存処理
                arrow_data = {
                    "info": {"id": item.id},
                    "waypoints": [[wp.pos().x(), wp.pos().y()] for wp in item.waypoints],
                }
                layout["arrow"][item.name] = arrow_data

        return layout

    def load_layout_yaml(self, layout_data):
        self.clear()
        self.block_objects.clear()
        self.arrow_objects.clear()

        # --- 1. ブロック作成 ---
        for block_key, block_value in layout_data.get("block", {}).items():
            info = block_value.get("info", {})
            block_type = info.get("type")
            block_filename = info.get("filename", "")
            block_id = info.get("id", 0)
            x = block_value.get("place", {}).get("x", 0)
            y = block_value.get("place", {}).get("y", 0)

            output_conn = block_value.get("connection", {}).get("output", {})
            # ch順でラベルを並べる
            ch_label_pairs = sorted(
                ((v.get("ch", 0), k) for k, v in output_conn.items()),
                key=lambda x: x[0]
            )
            labels = [label for ch, label in ch_label_pairs]

            if block_type == "frame":
                item = FrameBlockItem(block_id, block_filename)
            elif block_type == "if":
                item = IfBlockItem(block_id, block_filename)
            elif block_type == "switch":
                case_num = len(labels)
                item = SwitchBlockItem(block_id, block_filename, case_num)
                # ラベル順序を強制的に合わせる場合、ここでitem.output_sub_blocksを再構成してもよい
            else:
                continue

            item.setPos(x, y)
            self.addItem(item)
            self.block_objects[item.name] = item

        # --- 2. 矢印作成 ---
        for arrow_key, arrow_value in layout_data.get("arrow", {}).items():
            arrow_id = arrow_value.get("info", {}).get("id")
            waypoints = arrow_value.get("waypoints", [])

            arrow = ArrowItem(arrow_id)
            self.addItem(arrow)
            self.arrow_objects[arrow.name] = arrow

            for pos in waypoints:
                arrow.insert_waypoint(len(arrow.waypoints), QPointF(pos[0], pos[1]))

        # --- 3. 接続処理 ---
        for block_key, block_value in layout_data.get("block", {}).items():
            block = self.block_objects.get(block_key)
            if not block:
                continue

            output_conns = block_value.get("connection", {}).get("output", {})
            # ch順にソートして処理
            sorted_conns = sorted(
                output_conns.items(),
                key=lambda x: x[1].get("ch", 0)
            )

            for conn_idx, (output_pin, conn) in enumerate(sorted_conns):
                target_block_key = conn.get("target")
                arrow_key = conn.get("arrow")

                if not arrow_key or arrow_key not in self.arrow_objects:
                    continue

                arrow = self.arrow_objects[arrow_key]

                # 出力ブロック決定
                if isinstance(block, (IfBlockItem, SwitchBlockItem)):
                    labels = list(block.output_sub_blocks.keys())
                    output_pin = labels[conn_idx] if conn_idx < len(labels) else output_pin
                    output_block = block.output_sub_blocks.get(output_pin)
                else:
                    output_block = block

                # 接続設定
                arrow.start_item = output_block
                output_block.output_arrows.append(arrow)

                if target_block_key in self.block_objects:
                    target_block = self.block_objects[target_block_key]
                    arrow.end_item = target_block
                    target_block.input_arrows.append(arrow)

                # Update arrow direction
                if arrow.start_item:
                    start_center = arrow.start_item.sceneBoundingRect().center()
                    arrow.start_handle.setPos(start_center)
                if arrow.end_item:
                    end_center = arrow.end_item.sceneBoundingRect().center()
                    arrow.end_handle.setPos(end_center)
                arrow._force_snap_start = True
                arrow._force_snap_end = True
                arrow.update_path()

        return True

    def update_switch_block(self, condition_name, new_num_cases):
        target_block = None
        for block in self.block_objects.values():
            if isinstance(block, SwitchBlockItem) and block.filename == condition_name:
                target_block = block
                break

        if not target_block:
            return

        if target_block.num_cases == new_num_cases:
            return

        pos = target_block.pos()
        id = target_block.id

        # 現在の接続情報を保存
        input_arrows = list(target_block.input_arrows)
        old_output_labels = list(target_block.output_sub_blocks.keys())
        output_arrows = []
        for label in old_output_labels:
            subblock = target_block.output_sub_blocks[label]
            arrow = subblock.output_arrows[0] if subblock.output_arrows else None
            output_arrows.append(arrow)

        # ブロックだけ削除（矢印は削除しない）
        for arrow in input_arrows:
            arrow.end_item = None
        for arrow in output_arrows:
            if arrow:
                arrow.start_item = None

        self.removeItem(target_block)
        del self.block_objects[target_block.name]

        # 新しいブロックを作成
        new_block = SwitchBlockItem(id, condition_name, num_cases=new_num_cases)
        new_block.setPos(pos)
        self.addItem(new_block)
        self.block_objects[new_block.name] = new_block

        # 入力矢印を再接続
        for arrow in input_arrows:
            arrow.end_item = new_block
            new_block.input_arrows.append(arrow)
            arrow._force_snap_end = True
            arrow.update_path()

        # 出力矢印を再利用して再接続
        new_output_labels = list(new_block.output_sub_blocks.keys())
        min_output_count = min(len(output_arrows), len(new_output_labels))

        # 既存の矢印を再接続
        for i in range(min_output_count):
            arrow = output_arrows[i]
            if arrow:
                new_subblock = new_block.output_sub_blocks[new_output_labels[i]]
                arrow.start_item = new_subblock
                new_subblock.output_arrows.append(arrow)
                arrow._force_snap_start = True
                arrow.update_path()

        # 不要な矢印を削除（caseが減った場合）
        for i in range(min_output_count, len(output_arrows)):
            arrow = output_arrows[i]
            if arrow:
                if arrow.end_item:
                    arrow.end_item.input_arrows.remove(arrow)
                self.removeItem(arrow)
                if arrow.name in self.arrow_objects:
                    del self.arrow_objects[arrow.name]

        # 新しく増えたケースについては矢印なしの状態（何もしない）
