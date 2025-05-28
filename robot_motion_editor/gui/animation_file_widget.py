import os

from PyQt5.QtCore import QMimeData
from PyQt5.QtCore import QPoint
from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import QAbstractItemView
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtWidgets import QMenu
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QTreeWidget
from PyQt5.QtWidgets import QTreeWidgetItem

from ..logic.animation_file_manager import AnimationData
from ..logic.motion_directory_manager import MotionDirectoryManager


class AnimationFileWidget(QTreeWidget):
    itemDoubleClickedSignal = pyqtSignal(object)

    def __init__(self, motion_directory_manager: MotionDirectoryManager, parent=None):
        super().__init__(parent)
        self.motion_directory_manager = motion_directory_manager
        self.setHeaderLabel("Animations")
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)

    def on_item_double_clicked(self, item, column):
        self.itemDoubleClickedSignal.emit(item)

    def show_context_menu(self, pos: QPoint):
        item = self.itemAt(pos)
        if item is None:
            return

        menu = QMenu(self)

        if item.parent() is None:
            rename_action = menu.addAction("Rename Animation")
            action = menu.exec_(self.viewport().mapToGlobal(pos))
            if action == rename_action:
                self.rename_animation_folder(item)
            return

        parent_text = item.parent().text(0)
        if parent_text not in {"frames", "if", "switch"}:
            return

        rename_action = menu.addAction("Rename")
        action = menu.exec_(self.viewport().mapToGlobal(pos))

        if action == rename_action:
            old_name = item.text(0)
            new_name, ok = QInputDialog.getText(
                self, "Rename", f"Rename {parent_text} '{old_name}' to:", text=old_name)
            if ok and new_name and new_name != old_name:
                success = self.rename_yaml_file(parent_text, old_name, new_name, item)
                if success:
                    item.setText(0, new_name)

    def rename_animation_folder(self, item: QTreeWidgetItem):
        old_name = item.text(0)
        new_name, ok = QInputDialog.getText(self, "Rename", f"Rename Animation '{old_name}' to:", text=old_name)
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

        item.setText(0, new_name)
        if hasattr(self.parent(), "current_animation_name") and self.parent().current_animation_name == old_name:
            self.parent().current_animation_name = new_name

    def rename_yaml_file(self, category, old_name, new_name, item_widget):
        animation_item = item_widget
        while animation_item.parent():
            animation_item = animation_item.parent()
        animation_name = animation_item.text(0)

        if category == "frames":
            old_path = self.motion_directory_manager.resolve_frame_path(old_name, animation_name)
            new_path = self.motion_directory_manager.resolve_frame_path(new_name, animation_name)
        elif category == "if":
            old_path = self.motion_directory_manager.resolve_if_condition_path(old_name, animation_name)
            new_path = self.motion_directory_manager.resolve_if_condition_path(new_name, animation_name)
        elif category == "switch":
            old_path = self.motion_directory_manager.resolve_switch_condition_path(old_name, animation_name)
            new_path = self.motion_directory_manager.resolve_switch_condition_path(new_name, animation_name)
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

        editor = self
        while editor and not hasattr(editor, "scene"):
            editor = editor.parent()
        if not editor:
            QMessageBox.critical(self, "Error", "AnimationWidget not found.")
            return False

        anim_data = editor.scene.get_animation_data()
        anim_data_dict = anim_data.get_dict()
        block_dict = anim_data_dict.get("block", {})
        updated = False

        singular_type = category.rstrip("s")
        new_block = {}
        rename_map = {}

        for block_key, block_data in block_dict.items():
            info = block_data.get("info", {})
            block_type = info.get("type")
            block_filename = info.get("filename")
            block_id = info.get("id")

            if block_type == singular_type and block_filename == old_name:
                info["filename"] = new_name
                parts = block_key.split("_")
                if len(parts) >= 3 and parts[0] == singular_type and parts[2] == old_name:
                    new_key = f"{parts[0]}_{parts[1]}_{new_name}"
                    rename_map[block_key] = new_key
                    new_block[new_key] = block_data
                    updated = True
                else:
                    new_block[block_key] = block_data
            else:
                new_block[block_key] = block_data

        anim_data_dict["block"] = new_block

        for block_data in anim_data_dict["block"].values():
            output = block_data.get("connection", {}).get("output", {})
            for conn in output.values():
                if isinstance(conn, dict) and "target" in conn:
                    old_target = conn["target"]
                    if old_target in rename_map:
                        conn["target"] = rename_map[old_target]
                        updated = True

        if updated:
            new_anim_data = AnimationData()
            new_anim_data.set_dict(anim_data_dict)
            editor.scene.set_animation_data(new_anim_data)
            editor.save_current_animation()

        return True

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
