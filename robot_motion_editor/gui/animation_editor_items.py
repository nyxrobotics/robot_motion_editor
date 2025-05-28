import math

from PyQt5.QtCore import QPointF
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush
from PyQt5.QtGui import QColor
from PyQt5.QtGui import QFontMetricsF
from PyQt5.QtGui import QPainterPath
from PyQt5.QtGui import QPen
from PyQt5.QtWidgets import QGraphicsEllipseItem
from PyQt5.QtWidgets import QGraphicsPathItem
from PyQt5.QtWidgets import QGraphicsRectItem
from PyQt5.QtWidgets import QGraphicsTextItem


class StartBlockItem(QGraphicsRectItem):
    def __init__(self, id):
        self.type = "start"
        self.id = id
        self.name = f"{self.type}_{self.id}"
        self.max_inputs = 0
        self.max_outputs = 1
        self.input_arrows = []
        self.output_arrows = []

        super().__init__(0, 0, 100, 60)
        self.setBrush(QBrush(QColor("#0066cc")))  # 青系
        self.default_pen = QPen(QColor("white"), 3)
        self.setPen(self.default_pen)
        self.setFlags(self.ItemIsMovable | self.ItemIsSelectable | self.ItemSendsGeometryChanges)

        self.label = QGraphicsTextItem("Start", self)
        self.label.setDefaultTextColor(QColor("white"))
        self.label.setPos(
            (self.rect().width() - self.label.boundingRect().width()) / 2,
            (self.rect().height() - self.label.boundingRect().height()) / 2
        )

    def can_accept_input(self):
        return False

    def can_accept_output(self):
        return self.max_outputs == -1 or len(self.output_arrows) < self.max_outputs

    def paint(self, painter, option, widget=None):
        self.setPen(self.default_pen)
        super().paint(painter, option, widget)

    def itemChange(self, change, value):
        if change == self.ItemPositionChange and self.scene():
            for item in self.scene().items():
                if isinstance(item, ArrowItem):
                    if item.start_item == self or item.end_item == self:
                        item.update_path()
        return super().itemChange(change, value)

    def remove_from_scene(self):
        scene = self.scene()
        for arrow in list(self.output_arrows):
            arrow.remove_from_scene()
        self.output_arrows.clear()
        if scene:
            scene.removeItem(self)

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self.scene().editor_widget.on_start_block_double_clicked()


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
        self.scene().editor_widget.on_frame_block_double_clicked(self.filename)

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
        self.default_brush = QBrush(QColor("#2b2b2b"))
        self.preview_brush = QBrush(QColor(80, 120, 200))
        self.selected_brush = self.default_brush
        self.highlight_brush = self.default_brush
        self.default_pen = QPen(QColor("#aaaaaa"), 2)
        self.highlight_pen = QPen(QColor("#00ff00"), 3)
        self.selected_pen = QPen(QColor("#00ffff"), 3)
        self.setBrush(self.default_brush)
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

    def mousePressEvent(self, event):
        # クリック時に preview_index を反映
        if isinstance(self.parent_block, (IfBlockItem, SwitchBlockItem)):
            keys = list(self.parent_block.output_sub_blocks.keys())
            idx = keys.index(self.name)
            self.parent_block.preview_output_index = idx
            for sibling in self.parent_block.output_sub_blocks.values():
                sibling.update()

        # preview経路の再描画（Startからたどる）
        scene = self.scene()
        if hasattr(scene, "highlight_preview_path"):
            scene.highlight_preview_path()

        super().mousePressEvent(event)

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
        # 選択状態 → 選択用ペン
        if self.isSelected():
            self.setPen(self.selected_pen)
        elif self.is_highlighted:
            self.setPen(self.highlight_pen)
        else:
            self.setPen(self.default_pen)

        # 背景色の決定（preview_index による）
        brush = self.default_brush
        if isinstance(self.parent_block, (IfBlockItem, SwitchBlockItem)):
            keys = list(self.parent_block.output_sub_blocks.keys())
            if self.name in keys:
                idx = keys.index(self.name)
                if self.parent_block.preview_output_index == idx:
                    brush = self.preview_brush
        self.setBrush(brush)

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
        elif change == self.ItemSelectedChange:
            self.update()
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
        self.preview_output_index = 0

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
        self.scene().editor_widget.on_if_block_double_clicked(self.filename)

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
        self.preview_output_index = 0

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
        self.scene().editor_widget.on_switch_block_double_clicked(self.filename)

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

    def mousePressEvent(self, event):
        # Deselect other items
        if self.scene():
            for item in self.scene().selectedItems():
                if item is not self:
                    item.setSelected(False)
        self.setSelected(True)
        super().mousePressEvent(event)


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
        self.original_end_item = None

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
            if isinstance(item, (FrameBlockItem, IfBlockItem, SwitchBlockItem, OutputSubBlockItem, StartBlockItem)):
                is_same = (item == (self.arrow.start_item if self.is_start else self.arrow.end_item))

                # remove old connection
                if self.is_start and self.arrow.start_item:
                    if self.arrow in self.arrow.start_item.output_arrows:
                        self.arrow.start_item.output_arrows.remove(self.arrow)
                elif not self.is_start and self.arrow.end_item:
                    if self.arrow in self.arrow.end_item.input_arrows:
                        self.arrow.end_item.input_arrows.remove(self.arrow)

                # check max connections
                if self.is_start:
                    is_same = item == self.arrow.start_item
                    if item.max_outputs != -1 and len(item.output_arrows) >= item.max_outputs and not is_same:
                        target = None
                        break
                    item.output_arrows.append(self.arrow)
                else:
                    is_same = item == self.arrow.end_item
                    if item.max_inputs != -1 and len(item.input_arrows) >= item.max_inputs and not is_same:
                        target = None
                        break
                    item.input_arrows.append(self.arrow)
                target = item
                break

        if self.is_start:
            if self.arrow.start_item and self.arrow in self.arrow.start_item.output_arrows:
                self.arrow.start_item.output_arrows.remove(self.arrow)
            self.arrow.start_item = target
        else:
            if self.arrow.end_item and self.arrow in self.arrow.end_item.input_arrows:
                self.arrow.end_item.input_arrows.remove(self.arrow)
            self.arrow.end_item = target

        # reset highlights
        for item in scene.items():
            if hasattr(item, "set_highlighted"):
                item.set_highlighted(False)

        self.arrow.update_path()
        super().mouseReleaseEvent(event)

        # 💡 finally: rerun preview path with correct connections
        if hasattr(scene, "highlight_preview_path"):
            scene.highlight_preview_path()


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
        self.is_preview_path = False
        self.default_pen = QPen(QColor("#ffffff"), 3)
        self.selected_pen = QPen(QColor("#00ffff"), 4)
        self.preview_pen = QPen(QColor("#66ccff"), 3)
        self.highlight_pen = QPen(QColor("#00ff00"), 3)
        self.setPen(self.default_pen)
        self.setFlags(self.ItemIsSelectable)

    def compute_edge_point(self, center, target, width, height):
        dx = target.x() - center.x()
        dy = target.y() - center.y()
        if dx == 0 and dy == 0:
            return center
        scale = 0.5 / max(abs(dx) / width, abs(dy) / height)
        return QPointF(center.x() + dx * scale, center.y() + dy * scale)

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
        if self.isSelected():
            pen = self.selected_pen
        elif self.is_preview_path:
            pen = self.preview_pen
        else:
            pen = self.default_pen

        is_connected = self.start_item is not None and self.end_item is not None
        pen.setStyle(Qt.SolidLine if is_connected else Qt.DashLine)
        self.setPen(pen)

        if self.start_item and (self._force_snap_start or (
                not self.start_handle.is_dragging and (
                    not self.waypoints or self._recently_moved_waypoint is self.waypoints[0]
                ))):
            neighbor = self.waypoints[0].pos() if self.waypoints else self.end_handle.pos()
            center = self.start_item.sceneBoundingRect().center()
            p1 = self.compute_edge_point(center, neighbor,
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
            p2 = self.compute_edge_point(center, neighbor,
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
