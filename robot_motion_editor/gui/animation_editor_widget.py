import os

import yaml
from PyQt5.QtCore import QPointF
from PyQt5.QtCore import QRectF
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QAction
from PyQt5.QtWidgets import QGraphicsScene
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtWidgets import QMenu
from PyQt5.QtWidgets import QMessageBox

from ..logic.animation_file_manager import AnimationData
from ..logic.animation_file_manager import ArrowData
from ..logic.animation_file_manager import BlockConnection
from ..logic.animation_file_manager import BlockData
from ..logic.animation_file_manager import BlockInfo
from ..logic.frame_file_manager import FrameData
from ..logic.if_condition_file_manager import IfConditionData
from ..logic.motion_directory_manager import MotionDirectoryManager
from ..logic.switch_condition_file_manager import SwitchConditionData
from .animation_editor_items import ArrowItem
from .animation_editor_items import FrameBlockItem
from .animation_editor_items import IfBlockItem
from .animation_editor_items import OutputSubBlockItem
from .animation_editor_items import StartBlockItem
from .animation_editor_items import SwitchBlockItem
from .animation_editor_items import WaypointItem


class AnimationEditorWidget(QGraphicsScene):
    def __init__(self, motion_directory_manager: MotionDirectoryManager, parent=None):
        super().__init__(parent)

        self.motion_directory_manager = motion_directory_manager
        self.setBackgroundBrush(QColor("#111111"))
        self.block_objects = {}
        self.arrow_objects = {}
        self.setSceneRect(0, 0, 1000, 1000)
        self.editor_widget = None

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
            path = self.motion_directory_manager.resolve_switch_condition_path(name)
            switch_data = SwitchConditionData()
            switch_data.load_from_file(path)
            num_cases = len(switch_data.case) + 1 if switch_data.case else 2
            item = SwitchBlockItem(id, name, num_cases=num_cases)
        elif item_type == "start":
            if any(isinstance(b, StartBlockItem) for b in self.block_objects.values()):
                QMessageBox.warning(None, "Start Block Exists", "This animation already has a Start block.")
                return
            item = StartBlockItem(id)
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
        if isinstance(item, FrameBlockItem):
            delete_action = menu.addAction("Delete Frame Block")
            action = menu.exec_(event.screenPos())
            if action == delete_action:
                scene = self.scene()
                if scene:
                    scene.remove_block_and_arrows(self)
        elif isinstance(item, IfBlockItem):
            delete_action = menu.addAction("Delete If Block")
            action = menu.exec_(event.screenPos())
            if action == delete_action:
                scene = self.scene()
                if scene:
                    scene.remove_block_and_arrows(self)
        elif isinstance(item, SwitchBlockItem):
            delete_action = menu.addAction("Delete Switch Block")
            action = menu.exec_(event.screenPos())
            if action == delete_action:
                scene = self.scene()
                if scene:
                    scene.remove_block_and_arrows(self)
        elif isinstance(item, ArrowItem):
            delete_arrow_action = menu.addAction("Delete Arrow")
            action = menu.exec_(event.screenPos())
            if action == delete_arrow_action:
                scene = self.scene()
                if scene:
                    scene.remove_arrow(self)
        elif isinstance(item, OutputSubBlockItem):
            item.setSelected(True)
            item.contextMenuEvent(event)
        else:
            new_start_action = QAction("New Start", menu)
            new_frame_action = QAction("New Frame", menu)
            new_if_action = QAction("New If", menu)
            new_switch_action = QAction("New Switch", menu)
            new_arrow_action = QAction("New Arrow", menu)

            menu.addAction(new_start_action)
            menu.addAction(new_frame_action)
            menu.addAction(new_if_action)
            menu.addAction(new_switch_action)
            menu.addAction(new_arrow_action)

            selected_action = menu.exec_(event.screenPos())
            pos = event.scenePos()

            if selected_action == new_start_action:
                # 既に存在していれば拒否
                if any(isinstance(b, StartBlockItem) for b in self.block_objects.values()):
                    QMessageBox.warning(
                        None,
                        "Start Block Exists",
                        "There is already a Start block in this animation.")
                    return
                id = self._generate_block_id()
                block = StartBlockItem(id)
                block.setPos(pos)
                self.addItem(block)
                self.block_objects[block.name] = block
            elif selected_action == new_frame_action:
                name, ok = QInputDialog.getText(None, "New Frame", "Enter frame name:")
                if ok and name.strip():
                    name = name.strip()
                    frame_data = FrameData()
                    frame_path = self.motion_directory_manager.resolve_frame_path(name)
                    frame_data.save_to_file(frame_path)

                    id = self._generate_block_id()
                    block = FrameBlockItem(id, name)
                    block.setPos(pos)
                    self.addItem(block)
                    self.block_objects[block.name] = block

                    self.motion_directory_manager.list_animation()

            elif selected_action == new_if_action:
                name, ok = QInputDialog.getText(None, "New If Condition", "Enter condition name:")
                if ok and name.strip():
                    name = name.strip()
                    condition_data = IfConditionData(expression="", condition="")
                    condition_path = self.motion_directory_manager.resolve_if_condition_path(name)
                    condition_data.save_to_file(condition_path)

                    id = self._generate_block_id()
                    block = IfBlockItem(id, name)
                    block.setPos(pos)
                    self.addItem(block)
                    self.block_objects[block.name] = block

                    self.motion_directory_manager.list_animation()

            elif selected_action == new_switch_action:
                name, ok = QInputDialog.getText(None, "New Switch Condition", "Enter condition name:")
                if ok and name.strip():
                    name = name.strip()
                    condition_data = SwitchConditionData(expression="", condition="", case={"case_0": {"value": 0}})
                    condition_path = self.motion_directory_manager.resolve_switch_condition_path(name)
                    condition_data.save_to_file(condition_path)

                    id = self._generate_block_id()
                    block = SwitchBlockItem(id, name, num_cases=2)
                    block.setPos(pos)
                    self.addItem(block)
                    self.block_objects[block.name] = block

                    self.motion_directory_manager.list_animation()

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
            if arrow.name in self.arrow_objects:
                self.arrow_objects.pop(arrow.name)
            arrow.remove_from_scene()
        for arrow in list(getattr(block, 'output_arrows', [])):
            if arrow.name in self.arrow_objects:
                self.arrow_objects.pop(arrow.name)
            arrow.remove_from_scene()
        if block.name in self.block_objects:
            self.block_objects.pop(block.name)
        block.remove_from_scene()

    def remove_block(self, block):
        if block.name in self.block_objects:
            self.block_objects.pop(block.name)
        block.remove_from_scene()

    def remove_arrow(self, arrow):
        if arrow in self.arrow_objects:
            self.arrow_objects.pop(arrow.name)
        arrow.remove_from_scene()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            for item in self.selectedItems():
                if isinstance(item, (FrameBlockItem, IfBlockItem, SwitchBlockItem, StartBlockItem)):
                    self.remove_block(item)
                elif isinstance(item, (ArrowItem)):
                    self.remove_arrow(item)
                elif isinstance(item, WaypointItem):
                    arrow = item.arrow
                    if item in arrow.waypoints:
                        arrow.waypoints.remove(item)
                    self.removeItem(item)
                    arrow.update_path()
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

    def get_animation_data(self) -> AnimationData:
        anim_data = AnimationData()

        for item in self.items():
            if isinstance(item, (FrameBlockItem, IfBlockItem, SwitchBlockItem, StartBlockItem)):
                # BlockInfo
                info = BlockInfo(
                    type=item.type,
                    filename=getattr(item, "filename", ""),
                    id=item.id
                )

                # 位置
                place = {
                    "x": item.pos().x(),
                    "y": item.pos().y()
                }

                # 出力接続情報
                output = {}
                if isinstance(item, FrameBlockItem):
                    output_labels = ["out_0"]
                elif isinstance(item, (IfBlockItem, SwitchBlockItem)):
                    output_labels = list(item.output_sub_blocks.keys())
                elif isinstance(item, StartBlockItem):
                    output_labels = ["out_0"]
                else:
                    output_labels = []

                for idx, label in enumerate(output_labels):
                    subblock = item.output_sub_blocks.get(label) if hasattr(item, 'output_sub_blocks') else item
                    connection = {"ch": idx}
                    if subblock.output_arrows:
                        arrow = subblock.output_arrows[0]
                        if arrow.end_item:
                            connection.update({
                                "target": arrow.end_item.name,
                                "arrow": arrow.name
                            })
                    output[label] = connection

                # BlockData にまとめて登録
                anim_data.block[item.name] = BlockData(
                    info=info,
                    place=place,
                    connection=BlockConnection(output=output)
                )

            elif isinstance(item, ArrowItem):
                waypoints = [[wp.pos().x(), wp.pos().y()] for wp in item.waypoints]
                anim_data.arrow[item.name] = ArrowData(
                    info={"id": item.id},
                    waypoints=waypoints
                )

        return anim_data

    def set_animation_data(self, anim_data: AnimationData):
        self.clear()
        self.block_objects.clear()
        self.arrow_objects.clear()

        layout_data = anim_data.get_dict()

        # --- ブロックの読み込み ---
        for name, block in layout_data.get("block", {}).items():
            btype = block.get("info", {}).get("type")
            filename = block.get("info", {}).get("filename", "")
            id = block.get("info", {}).get("id", 0)
            x = block.get("place", {}).get("x", 0)
            y = block.get("place", {}).get("y", 0)

            if btype == "frame":
                item = FrameBlockItem(id, filename)
            elif btype == "if":
                item = IfBlockItem(id, filename)
            elif btype == "switch":
                labels = list(block.get("connection", {}).get("output", {}).keys())
                item = SwitchBlockItem(id, filename, num_cases=len(labels))
            elif btype == "start":
                item = StartBlockItem(id)
            else:
                continue

            item.setPos(x, y)
            self.addItem(item)
            self.block_objects[item.name] = item

        # --- 矢印の読み込み ---
        for name, arrow in layout_data.get("arrow", {}).items():
            arrow_id = arrow.get("info", {}).get("id")
            waypoints = arrow.get("waypoints", [])

            item = ArrowItem(arrow_id)
            self.addItem(item)
            self.arrow_objects[item.name] = item

            for pos in waypoints:
                item.insert_waypoint(len(item.waypoints), QPointF(pos[0], pos[1]))

        # --- 接続構築 ---
        for block_name, block in layout_data.get("block", {}).items():
            source_block = self.block_objects.get(block_name)
            if not source_block:
                continue

            conns = block.get("connection", {}).get("output", {})
            sorted_items = sorted(conns.items(), key=lambda x: x[1].get("ch", 0))

            for idx, (label, conn) in enumerate(sorted_items):
                arrow_name = conn.get("arrow")
                target_name = conn.get("target")

                if arrow_name not in self.arrow_objects:
                    continue
                arrow = self.arrow_objects[arrow_name]

                # start_item
                if isinstance(source_block, (IfBlockItem, SwitchBlockItem)):
                    labels = list(source_block.output_sub_blocks.keys())
                    output_block = source_block.output_sub_blocks.get(labels[idx])
                else:
                    output_block = source_block

                arrow.start_item = output_block
                output_block.output_arrows.append(arrow)

                if target_name in self.block_objects:
                    target = self.block_objects[target_name]
                    arrow.end_item = target
                    target.input_arrows.append(arrow)

                arrow._force_snap_start = True
                arrow._force_snap_end = True
                arrow.update_path()

        self.update_scene_rect()

    def update_switch_block(self, filename, new_num_cases):
        target_block = None
        for block in self.block_objects.values():
            if isinstance(block, SwitchBlockItem) and block.filename == filename:
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
        new_block = SwitchBlockItem(id, filename, num_cases=new_num_cases)
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

    def find_previous_frame_block(self, block):
        input_sources = []
        for arrow in self.arrow_objects.values():
            if arrow.end_item == block:
                input_sources.append(arrow.start_item)

        if not input_sources:
            return None

        # 入力が1本ならそれだけをたどればよい
        if len(input_sources) == 1:
            source = input_sources[0]
            if isinstance(source, FrameBlockItem):
                return source
            return self.find_previous_frame_block(source)

        # 複数入力がある場合
        for source in input_sources:
            if isinstance(source, FrameBlockItem) and self._is_reachable_from_start(source):
                return source

        # どれも Start からつながっていなければ最初のFrameを返す
        for source in input_sources:
            if isinstance(source, FrameBlockItem):
                return source
            result = self.find_previous_frame_block(source)
            if result:
                return result
        return None

    def find_next_frame_block(self, block):
        for arrow in self.arrow_objects.values():
            if arrow.start_item == block:
                target = arrow.end_item
                if isinstance(target, FrameBlockItem):
                    return target
                else:
                    result = self.find_next_frame_block(target)
                    if result:
                        return result
        return None

    def _is_reachable_from_start(self, block, visited=None):
        if visited is None:
            visited = set()

        if block in visited:
            return False
        visited.add(block)

        if isinstance(block, StartBlockItem):
            return True

        for arrow in self.arrow_objects.values():
            if arrow.end_item == block:
                if self._is_reachable_from_start(arrow.start_item, visited):
                    return True
        return False

    def highlight_preview_path(self):
        for arrow in self.arrow_objects.values():
            arrow.is_preview_path = False
            arrow.update_path()

        visited_ids = set()

        def dfs(block):
            if not hasattr(block, 'id'):
                return
            if block.id in visited_ids:
                return
            visited_ids.add(block.id)

            if isinstance(block, (IfBlockItem, SwitchBlockItem)):
                outputs = list(block.output_sub_blocks.values())
                if outputs:
                    idx = block.preview_output_index
                    if idx < len(outputs):
                        sub = outputs[idx]
                        if sub.output_arrows:
                            arrow = sub.output_arrows[0]
                            arrow.is_preview_path = True
                            arrow.update_path()
                            dfs(arrow.end_item)
                return

            if hasattr(block, "output_arrows"):
                for arrow in block.output_arrows:
                    arrow.is_preview_path = True
                    arrow.update_path()
                    dfs(arrow.end_item)

        for block in self.block_objects.values():
            if isinstance(block, StartBlockItem):
                dfs(block)
                break

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()
