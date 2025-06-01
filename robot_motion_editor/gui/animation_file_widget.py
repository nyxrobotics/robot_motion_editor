import os
import shutil

import rospy
import yaml
from PyQt5.QtCore import QMimeData
from PyQt5.QtCore import QPoint
from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import QAbstractItemView
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtWidgets import QMenu
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QTreeWidget
from PyQt5.QtWidgets import QTreeWidgetItem

from ..logic.animation_file_manager import AnimationData
from ..logic.frame_file_manager import FrameData
from ..logic.if_condition_file_manager import IfConditionData
from ..logic.motion_directory_manager import MotionDirectoryManager
from ..logic.switch_condition_file_manager import SwitchConditionData
from .frame_editor import FrameEditorDialog
from .if_condition_editor import IfConditionEditorDialog
from .initial_frame_editor import InitialFrameEditorDialog
from .switch_condition_editor import SwitchConditionEditorDialog


class AnimationFileWidget(QTreeWidget):
    itemDoubleClickedSignal = pyqtSignal(object)

    def __init__(
        self,
        motion_directory_manager: MotionDirectoryManager,
        joint_data_manager=None,
        trajectory_visualizer=None,
        trajectory_commander=None,
        editor_scene=None,
        parent=None
    ):
        super().__init__(parent)
        self.open_editors = {}  # e.g. {"initial_frame": dlg, "frame:walk1": dlg}
        self.motion_directory_manager = motion_directory_manager
        self.joint_data_manager = joint_data_manager
        self.trajectory_visualizer = trajectory_visualizer
        self.trajectory_commander = trajectory_commander
        self.editor_scene = editor_scene
        self.setHeaderLabel("Animations")
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)

        self.header().setContextMenuPolicy(Qt.CustomContextMenu)
        self.header().customContextMenuRequested.connect(self.on_header_context_menu)

    def on_item_double_clicked(self, item, column):
        self.itemDoubleClickedSignal.emit(item)

    def show_context_menu(self, pos: QPoint):
        item = self.itemAt(pos)
        menu = QMenu(self)

        if item is None:
            action = menu.addAction("New Animation")
            selected = menu.exec_(self.viewport().mapToGlobal(pos))
            if selected == action:
                self.create_new_animation()
            return

        parent = item.parent()
        text = item.text(0)

        if parent is None:
            rename_action = menu.addAction("Rename Animation")
            delete_action = menu.addAction("Delete Animation")
            selected = menu.exec_(self.viewport().mapToGlobal(pos))

            if selected == rename_action:
                self.rename_animation_folder(item)

            elif selected == delete_action:
                self.delete_animation_folder(item)
            return

        if text in {"frames", "if", "switch"}:
            if text == "frames":
                action = menu.addAction("New Frame")
            elif text == "if":
                action = menu.addAction("New If")
            elif text == "switch":
                action = menu.addAction("New Switch")

            selected = menu.exec_(self.viewport().mapToGlobal(pos))
            if selected == action:
                self.setCurrentItem(item)
                if text == "frames":
                    self.create_new_frame()
                elif text == "if":
                    self.create_new_if()
                elif text == "switch":
                    self.create_new_switch()
            return

        if parent and parent.text(0) in {"frames", "if", "switch"}:
            rename_action = menu.addAction("Rename")
            delete_action = menu.addAction("Delete")
            selected = menu.exec_(self.viewport().mapToGlobal(pos))

            if selected == rename_action:
                old_name = item.text(0)
                new_name, ok = QInputDialog.getText(self, "Rename", f"Rename '{old_name}' to:", text=old_name)
                if ok and new_name and new_name != old_name:
                    success = self.rename_yaml_file(parent.text(0), old_name, new_name.strip(), item)
                    if success:
                        self.update_scene_after_rename()

            elif selected == delete_action:
                self.delete_file_item(parent.text(0), item.text(0))

    def on_header_context_menu(self, pos):
        global_pos = self.header().mapToGlobal(pos)
        menu = QMenu(self)
        action = menu.addAction("New Animation")
        selected = menu.exec_(global_pos)
        if selected == action:
            self.create_new_animation()

    def rename_animation_folder(self, item: QTreeWidgetItem):
        old_name = item.text(0)
        new_name, ok = QInputDialog.getText(self, "Rename Animation", f"Rename '{old_name}' to:", text=old_name)
        if not ok or not new_name or old_name == new_name:
            return

        old_path = self.motion_directory_manager.resolve_animation_path(old_name)
        new_path = self.motion_directory_manager.resolve_animation_path(new_name)

        if os.path.exists(new_path):
            QMessageBox.warning(self, "Error", f"'{new_name}' already exists.")
            return

        try:
            os.rename(old_path, new_path)
        except Exception as e:
            QMessageBox.critical(self, "Rename Failed", str(e))
            return

        # アニメーション名の更新
        if self.motion_directory_manager.get_current_animation() == old_name:
            self.motion_directory_manager.set_current_animation(new_name)
        else:
            self.motion_directory_manager.set_current_animation(None)

        # 完全にリロード（←ここが重要）
        self.clear()
        self.reload_animation_list()
        for i in range(self.topLevelItemCount()):
            anim = self.topLevelItem(i).text(0)
            self.reload_animation_contents(anim)

        # シーンも更新
        self.setCurrentItem(None)
        self.update_scene_after_rename()

    def delete_animation_folder(self, item: QTreeWidgetItem):
        name = item.text(0)
        path = self.motion_directory_manager.resolve_animation_path(name)

        reply = QMessageBox.question(
            self, "Delete Animation", f"Are you sure you want to delete animation '{name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                shutil.rmtree(path)
            except Exception as e:
                QMessageBox.critical(self, "Delete Failed", str(e))
                return

            if self.motion_directory_manager.get_current_animation() == name:
                self.motion_directory_manager.set_current_animation(None)

            self.reload_animation_list()
            if hasattr(self, "editor_scene"):
                self.editor_scene.clear()

    def rename_yaml_file(self, category, old_name, new_name, item_widget):
        # animation_name の決定
        animation_item = item_widget
        if animation_item:
            while animation_item.parent():
                animation_item = animation_item.parent()
            animation_name = animation_item.text(0)
        else:
            animation_name = self.motion_directory_manager.get_current_animation()

        if not animation_name:
            return False

        self.motion_directory_manager.set_current_animation(animation_name)

        # ファイルのパス設定
        if category == "frames":
            old_path = self.motion_directory_manager.resolve_frame_path(old_name)
            new_path = self.motion_directory_manager.resolve_frame_path(new_name)
        elif category == "if":
            old_path = self.motion_directory_manager.resolve_if_condition_path(old_name)
            new_path = self.motion_directory_manager.resolve_if_condition_path(new_name)
        elif category == "switch":
            old_path = self.motion_directory_manager.resolve_switch_condition_path(old_name)
            new_path = self.motion_directory_manager.resolve_switch_condition_path(new_name)
        else:
            return False

        if os.path.exists(new_path):
            QMessageBox.warning(self, "Error", f"'{new_name}.yaml' already exists.")
            return False

        try:
            os.rename(old_path, new_path)
        except Exception as e:
            QMessageBox.critical(self, "Rename Failed", str(e))
            return False

        # animation.yaml の更新
        yaml_path = self.motion_directory_manager.resolve_animation_yaml_path()
        if not os.path.exists(yaml_path):
            return False

        anim_data = AnimationData()
        anim_data.load_from_file(yaml_path)
        anim_data_dict = anim_data.get_dict()
        block_dict = anim_data_dict.get("block", {})
        updated = False
        rename_map = {}
        new_block = {}
        singular_type = category.rstrip("s")

        for block_key, block_data in block_dict.items():
            info = block_data.get("info", {})
            if info.get("type") == singular_type and info.get("filename") == old_name:
                info["filename"] = new_name
                parts = block_key.split("_", 2)
                if len(parts) == 3 and parts[0] == singular_type and parts[2] == old_name:
                    new_key = f"{parts[0]}_{parts[1]}_{new_name}"
                    rename_map[block_key] = new_key
                    new_block[new_key] = block_data
                    updated = True
                else:
                    new_block[block_key] = block_data
            else:
                new_block[block_key] = block_data

        # target名を更新
        for block_data in new_block.values():
            output = block_data.get("connection", {}).get("output", {})
            for conn in output.values():
                if isinstance(conn, dict) and "target" in conn:
                    if conn["target"] in rename_map:
                        conn["target"] = rename_map[conn["target"]]
                        updated = True

        if updated:
            anim_data_dict["block"] = new_block
            anim_data.set_dict(anim_data_dict)
            anim_data.save_to_file(yaml_path)

        # GUI再読み込み
        self.reload_animation_contents(animation_name)
        return True

    def update_scene_after_rename(self):
        animation_name = self.motion_directory_manager.get_current_animation()
        if not animation_name:
            return

        yaml_path = self.motion_directory_manager.resolve_animation_yaml_path()
        if not os.path.exists(yaml_path):
            return

        anim_data = AnimationData()
        anim_data.load_from_file(yaml_path)
        if hasattr(self.editor_scene, "set_animation_data"):
            self.editor_scene.set_animation_data(anim_data)

    def mouseMoveEvent(self, event):
        item = self.currentItem()
        if item is None:
            event.ignore()
            return
        elif item.text(0) == "initial_frame" and item.parent():
            item_type = "start"
        elif item and item.parent():
            parent_text = item.parent().text(0)
            if parent_text == "frames":
                item_type = "frame"
            elif parent_text == "if":
                item_type = "if"
            elif parent_text == "switch":
                item_type = "switch"
            else:
                event.ignore()
                return
        else:
            event.ignore()
            return

        mime_text = f"{item_type}:{item.text(0)}"
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(mime_text)
        drag.setMimeData(mime)
        drag.exec_(Qt.CopyAction)

    def create_new_frame(self, animation_name=None):
        if not animation_name:
            item = self.currentItem()
            while item and item.parent():
                item = item.parent()
            animation_name = item.text(0) if item else None

        if not animation_name:
            QMessageBox.warning(self, "No Animation Selected", "Please select an animation.")
            return

        self.motion_directory_manager.set_current_animation(animation_name)
        name, ok = QInputDialog.getText(self, "New Frame", "Enter frame name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        path = self.motion_directory_manager.resolve_frame_path(name)
        if os.path.exists(path):
            QMessageBox.warning(self, "Conflict", f"Frame '{name}' already exists.")
            return
        frame_data = FrameData(joint_names=self.motion_directory_manager.get_joint_names())
        frame_data.save_to_file(path)
        self.reload_animation_contents(animation_name)
        return name

    def create_new_if(self, animation_name=None):
        if not animation_name:
            item = self.currentItem()
            while item and item.parent():
                item = item.parent()
            animation_name = item.text(0) if item else None

        if not animation_name:
            QMessageBox.warning(self, "No Animation Selected", "Please select an animation.")
            return

        self.motion_directory_manager.set_current_animation(animation_name)
        name, ok = QInputDialog.getText(self, "New If Condition", "Enter condition name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        path = self.motion_directory_manager.resolve_if_condition_path(name)
        if os.path.exists(path):
            QMessageBox.warning(self, "Conflict", f"If condition '{name}' already exists.")
            return
        if_data = IfConditionData(expression="", condition="")
        if_data.save_to_file(path)
        self.reload_animation_contents(animation_name)
        return name

    def create_new_switch(self, animation_name=None):
        if not animation_name:
            item = self.currentItem()
            while item and item.parent():
                item = item.parent()
            animation_name = item.text(0) if item else None

        if not animation_name:
            QMessageBox.warning(self, "No Animation Selected", "Please select an animation.")
            return

        self.motion_directory_manager.set_current_animation(animation_name)
        name, ok = QInputDialog.getText(self, "New Switch Condition", "Enter condition name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        path = self.motion_directory_manager.resolve_switch_condition_path(name)
        if os.path.exists(path):
            QMessageBox.warning(self, "Conflict", f"Switch condition '{name}' already exists.")
            return

        switch_data = SwitchConditionData(expression="", condition="", case={"case_0": {"value": 0}})
        switch_data.save_to_file(path)
        self.reload_animation_contents(animation_name)
        return name

    def delete_file_item(self, category, name):
        animation_name = self.motion_directory_manager.get_current_animation()
        if not animation_name:
            return
        if category == "frames":
            path = self.motion_directory_manager.resolve_frame_path(name)
        elif category == "if":
            path = self.motion_directory_manager.resolve_if_condition_path(name)
        elif category == "switch":
            path = self.motion_directory_manager.resolve_switch_condition_path(name)
        else:
            return

        reply = QMessageBox.question(self, "Delete", f"Delete {category} '{name}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes and os.path.exists(path):
            os.remove(path)
            self.reload_animation_contents(animation_name)

    def reload_animation_list(self):
        self.clear()
        base_dir = self.motion_directory_manager.get_motion_directory()
        if not os.path.isdir(base_dir):
            return

        for animation_name in sorted(os.listdir(base_dir)):
            path = os.path.join(base_dir, animation_name)
            if os.path.isdir(path):
                anim_item = QTreeWidgetItem([animation_name])
                self.addTopLevelItem(anim_item)

    def reload_animation_contents(self, animation_name: str):
        base_dir = self.motion_directory_manager.get_motion_directory()
        anim_path = os.path.join(base_dir, animation_name)
        if not os.path.isdir(anim_path):
            return

        # 親ノードを探す（なければ作る）
        for i in range(self.topLevelItemCount()):
            if self.topLevelItem(i).text(0) == animation_name:
                parent_item = self.topLevelItem(i)
                parent_item.takeChildren()
                break
        else:
            parent_item = QTreeWidgetItem([animation_name])
            self.addTopLevelItem(parent_item)

        # initial_frame
        QTreeWidgetItem(parent_item, ["initial_frame"])

        # frames
        frames_item = QTreeWidgetItem(parent_item, ["frames"])
        self.motion_directory_manager.set_current_animation(animation_name)
        for frame in self.motion_directory_manager.list_frame_files():
            QTreeWidgetItem(frames_item, [frame])

        # conditions/if
        conditions_item = QTreeWidgetItem(parent_item, ["conditions"])
        if_item = QTreeWidgetItem(conditions_item, ["if"])
        for cond in self.motion_directory_manager.list_if_condition_files():
            QTreeWidgetItem(if_item, [cond])

        # conditions/switch
        switch_item = QTreeWidgetItem(conditions_item, ["switch"])
        for cond in self.motion_directory_manager.list_switch_condition_files():
            QTreeWidgetItem(switch_item, [cond])

    def open_editor_by_type(self, type: str, name: str = ""):
        key = f"{type}:{name}" if name else type
        if key in self.open_editors and self.open_editors[key].isVisible():
            self.open_editors[key].raise_()
            self.open_editors[key].activateWindow()
            return

        if type == "initial_frame":
            dlg = InitialFrameEditorDialog(
                joint_data_manager=self.joint_data_manager,
                motion_directory_manager=self.motion_directory_manager,
                trajectory_visualizer=self.trajectory_visualizer,
                trajectory_commander=self.trajectory_commander
            )
        elif type == "frame":
            dlg = FrameEditorDialog(
                joint_data_manager=self.joint_data_manager,
                motion_directory_manager=self.motion_directory_manager,
                filename=name,
                trajectory_visualizer=self.trajectory_visualizer,
                trajectory_commander=self.trajectory_commander
            )
        elif type == "if":
            dlg = IfConditionEditorDialog(
                joint_data_manager=self.joint_data_manager,
                motion_directory_manager=self.motion_directory_manager,
                filename=name
            )
        elif type == "switch":
            dlg = SwitchConditionEditorDialog(
                joint_data_manager=self.joint_data_manager,
                motion_directory_manager=self.motion_directory_manager,
                filename=name
            )
            dlg.finished.connect(lambda result_code: (
                self.animation_flow_scene.update_switch_block(name, dlg.result.get("num_cases", 2))
                if result_code == QDialog.Accepted and dlg.result else None
            ))
        else:
            rospy.logwarn(f"[AnimaitonWidget] Unknown editor type: {type}")
            return

        dlg.setAttribute(Qt.WA_DeleteOnClose)
        dlg.show()
        self.open_editors[key] = dlg
        dlg.destroyed.connect(lambda: self.open_editors.pop(key, None))

    def create_new_animation(self):
        name, ok = QInputDialog.getText(self, "New Animation", "Enter animation name:")
        if not ok or not name.strip():
            return
        name = name.strip()

        base_dir = self.motion_directory_manager.get_motion_directory()
        animation_path = os.path.join(base_dir, name)
        if os.path.exists(animation_path):
            QMessageBox.warning(self, "Name Conflict", f"Animation '{name}' already exists.")
            return

        os.makedirs(os.path.join(animation_path, "frames"), exist_ok=True)
        os.makedirs(os.path.join(animation_path, "conditions", "if"), exist_ok=True)
        os.makedirs(os.path.join(animation_path, "conditions", "switch"), exist_ok=True)

        with open(os.path.join(animation_path, f"{name}.yaml"), "w") as f:
            f.write("# animation flowchart")
        with open(os.path.join(animation_path, "initial_frame.yaml"), "w") as f:
            f.write("# initial frame")

        self.reload_animation_contents(name)
        return name

    def delete_animation(self):
        item = self.currentItem()
        if not item or item.parent() is not None:
            QMessageBox.warning(self, "Selection Error", "Please select an animation to delete.")
            return
        name = item.text(0)
        path = os.path.join(self.motion_directory_manager.get_motion_directory(), name)

        reply = QMessageBox.question(
            self,
            "Delete Animation",
            f"Are you sure you want to delete animation '{name}'?",
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            shutil.rmtree(path, ignore_errors=True)
            self.motion_directory_manager.set_current_animation(None)
            self.reload_animation_contents(name)
            self.motion_directory_manager.set_current_animation(None)

    def delete_frame(self):
        item = self.currentItem()
        parent = item.parent() if item else None
        if not item or not parent:
            QMessageBox.warning(self, "Selection Error", "Please select a frame to delete.")
            return

        animation_item = item
        while animation_item.parent():
            animation_item = animation_item.parent()
        animation_name = animation_item.text(0)

        self.motion_directory_manager.set_current_animation(animation_name)

        frame_name = item.text(0)
        frame_path = self.motion_directory_manager.resolve_frame_path(frame_name)

        reply = QMessageBox.question(
            self,
            "Delete Frame",
            f"Are you sure you want to delete frame '{frame_name}'?",
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes and os.path.exists(frame_path):
            os.remove(frame_path)
            self.reload_animation_contents(animation_name)
