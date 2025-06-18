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
from ..logic.motion_file_manager import MotionFileManager
from ..logic.switch_condition_file_manager import SwitchConditionData
from .animation_item_editor_launcher import AnimationItemEditorLauncher


class AnimationFileWidget(QTreeWidget):
    itemDoubleClickedSignal = pyqtSignal(object)

    def __init__(
        self,
        motion_file_manager: MotionFileManager,
        joint_data_manager=None,
        trajectory_visualizer=None,
        trajectory_commander=None,
        editor_launcher: AnimationItemEditorLauncher = None,
        parent=None
    ):
        super().__init__(parent)
        self.open_editors = {}  # e.g. {"initial_frame": dlg, "frame:walk1": dlg}
        self.motion_file_manager = motion_file_manager
        self.joint_data_manager = joint_data_manager
        self.trajectory_visualizer = trajectory_visualizer
        self.trajectory_commander = trajectory_commander
        self.editor_launcher = editor_launcher
        self.setHeaderLabel("Animations")
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)

        self.header().setContextMenuPolicy(Qt.CustomContextMenu)
        self.header().customContextMenuRequested.connect(self.on_header_context_menu)

    def on_item_double_clicked(self, item, column):
        self.itemDoubleClickedSignal.emit(item)

        animation_item = item
        while animation_item.parent():
            animation_item = animation_item.parent()
        animation_name = animation_item.text(0)
        self.motion_file_manager.set_animation_name(animation_name)

        label = item.text(0)
        parent = item.parent().text(0) if item.parent() else ""

        if label == "initial_frame":
            self.editor_launcher.open_editor_by_type("initial_frame")
        elif parent == "frames":
            self.editor_launcher.open_editor_by_type("frame", label)
        elif parent == "if":
            self.editor_launcher.open_editor_by_type("if", label)
        elif parent == "switch":
            self.editor_launcher.open_editor_by_type("switch", label)
        else:
            rospy.logwarn("[AnimationFileWidget] Unknown tree item type")

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
                    if item.parent().text(0) == "frames":
                        self.motion_file_manager.rename_frame(old_name=old_name, new_name=new_name.strip())
                    elif item.parent().text(0) == "if":
                        self.motion_file_manager.rename_if(old_name=old_name, new_name=new_name.strip())
                    elif item.parent().text(0) == "switch":
                        self.motion_file_manager.rename_switch(old_name=old_name, new_name=new_name.strip())
                    else:
                        QMessageBox.warning(self, "Error", "Cannot rename this item.")
                    rospy.loginfo(
                        f"[AnimationFileWidget] Renamed {item.parent().text(0)}: {old_name} -> {new_name.strip()}")
                    self.reload_file_lists(self.motion_file_manager.get_animation_name())

            elif selected == delete_action:
                if item.parent().text(0) == "frames":
                    self.motion_file_manager.delete_frame(item.text(0))
                elif item.parent().text(0) == "if":
                    self.motion_file_manager.delete_if(item.text(0))
                elif item.parent().text(0) == "switch":
                    self.motion_file_manager.delete_switch(item.text(0))
                else:
                    QMessageBox.warning(self, "Error", "Cannot delete this item.")
                rospy.loginfo(f"[AnimationFileWidget] Deleted {item.parent().text(0)}: {item.text(0)}")
                self.reload_file_lists(self.motion_file_manager.get_animation_name())

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
        self.motion_file_manager.rename_animation(old_name=old_name, new_name=new_name.strip())

    def delete_animation_folder(self, item: QTreeWidgetItem):
        name = item.text(0)
        self.motion_file_manager.delete_animation(name)

    def reload_scene(self):
        rospy.loginfo("[AnimationFileWidget] Reloading animation scene")
        animation_name = self.motion_file_manager.get_animation_name()
        self.reload_file_lists(animation_name)

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

        self.motion_file_manager.set_animation_name(animation_name)
        name, ok = QInputDialog.getText(self, "New Frame", "Enter frame name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        self.motion_file_manager.set_frame(name)

    def create_new_if(self, animation_name=None):
        if not animation_name:
            item = self.currentItem()
            while item and item.parent():
                item = item.parent()
            animation_name = item.text(0) if item else None

        if not animation_name:
            QMessageBox.warning(self, "No Animation Selected", "Please select an animation.")
            return

        self.motion_file_manager.set_animation_name(animation_name)
        name, ok = QInputDialog.getText(self, "New If Condition", "Enter condition name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if_data = IfConditionData(expression="", condition="")
        self.motion_file_manager.set_if(name, if_data)

    def create_new_switch(self, animation_name=None):
        if not animation_name:
            item = self.currentItem()
            while item and item.parent():
                item = item.parent()
            animation_name = item.text(0) if item else None

        if not animation_name:
            QMessageBox.warning(self, "No Animation Selected", "Please select an animation.")
            return

        self.motion_file_manager.set_animation_name(animation_name)
        name, ok = QInputDialog.getText(self, "New Switch Condition", "Enter condition name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        switch_data = SwitchConditionData(expression="", condition="", cases={})
        self.motion_file_manager.set_switch(name, switch_data)

    def reload_animation_list(self):
        self.clear()
        base_dir = self.motion_file_manager.get_motion_directory()
        if not os.path.isdir(base_dir):
            return

        for animation_name in sorted(os.listdir(base_dir)):
            path = os.path.join(base_dir, animation_name)
            if os.path.isdir(path):
                anim_item = QTreeWidgetItem([animation_name])
                self.addTopLevelItem(anim_item)

    def reload_file_lists(self, animation_name: str):
        base_dir = self.motion_file_manager.get_motion_directory()
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
        self.motion_file_manager.set_animation_name(name=animation_name, skip_load=True)
        for frame in self.motion_file_manager.list_frame_files():
            QTreeWidgetItem(frames_item, [frame])

        # conditions/if
        conditions_item = QTreeWidgetItem(parent_item, ["conditions"])
        if_item = QTreeWidgetItem(conditions_item, ["if"])
        for cond in self.motion_file_manager.list_if_condition_files():
            QTreeWidgetItem(if_item, [cond])

        # conditions/switch
        switch_item = QTreeWidgetItem(conditions_item, ["switch"])
        for cond in self.motion_file_manager.list_switch_condition_files():
            QTreeWidgetItem(switch_item, [cond])
