
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

from ..logic.frame_file_manager import FrameData
from ..logic.frame_file_manager import FrameFileManager
from ..logic.if_condition_file_manager import IfConditionData
from ..logic.if_condition_file_manager import IfConditionFileManager
from ..logic.switch_condition_file_manager import save_switch_condition
from .animation_editor_items import ArrowItem
from .animation_editor_items import FrameBlockItem
from .animation_editor_items import IfBlockItem
from .animation_editor_items import OutputSubBlockItem
from .animation_editor_items import StartBlockItem
from .animation_editor_items import SwitchBlockItem
from .animation_editor_items import WaypointItem


class AnimationEditorWidget(QGraphicsScene):
    def __init__(self, editor_widget, parent=None):
        super().__init__(parent)
        self.editor_widget = editor_widget
        self.setBackgroundBrush(QColor("#111111"))
        self.block_objects = {}
        self.arrow_objects = {}
        self.setSceneRect(0, 0, 1000, 1000)

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
                self.editor_widget.motion_directory,
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
        elif item_type == "start":
            # 既にStartBlockが存在するかチェック
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
                    frames_dir = os.path.join(
                        self.editor_widget.motion_directory,
                        self.editor_widget.current_animation_name,
                        "frames")
                    frame_path = os.path.join(frames_dir, f"{name}.yaml")

                    if os.path.exists(frame_path):
                        QMessageBox.warning(None, "Name Conflict", f"Frame '{name}' already exists.")
                        return

                    os.makedirs(frames_dir, exist_ok=True)
                    default_frame_data = FrameData().get_dict()
                    FrameFileManager.save_dict(
                        os.path.dirname(frame_path),
                        default_frame_data,
                        os.path.basename(frame_path))

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
                        self.editor_widget.motion_directory,
                        self.editor_widget.current_animation_name,
                        "conditions",
                        "if")
                    condition_path = os.path.join(conditions_dir, f"{name}.yaml")

                    if os.path.exists(condition_path):
                        QMessageBox.warning(None, "Name Conflict", f"If condition '{name}' already exists.")
                        return

                    os.makedirs(conditions_dir, exist_ok=True)
                    default_if_data = IfConditionData(expression="", condition="")
                    IfConditionFileManager.save_dict(
                        conditions_dir,
                        default_if_data.get_dict(),
                        f"{name}.yaml"
                    )

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
                        self.editor_widget.motion_directory,
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
                        self.editor_widget.motion_directory,
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

    def save_layout_yaml(self):
        layout = {"block": {}, "arrow": {}}

        for item in self.items():
            if isinstance(item, (FrameBlockItem, IfBlockItem, SwitchBlockItem, StartBlockItem)):
                block_data = {
                    "info": {
                        "type": item.type,
                        "filename": getattr(item, "filename", ""),  # StartBlockItem は filename 持たないがOK
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

                # 出力接続の構成（Start, Frame, If, Switch）
                output_labels = []
                if isinstance(item, FrameBlockItem):
                    output_labels = ["out_0"]
                elif isinstance(item, (IfBlockItem, SwitchBlockItem)):
                    output_labels = list(item.output_sub_blocks.keys())
                elif isinstance(item, StartBlockItem):
                    output_labels = ["out_0"]

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
                layout["arrow"][item.name] = {
                    "info": {"id": item.id},
                    "waypoints": [[wp.pos().x(), wp.pos().y()] for wp in item.waypoints],
                }

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
            elif block_type == "start":
                item = StartBlockItem(block_id)
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
        self.update_scene_rect()
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
