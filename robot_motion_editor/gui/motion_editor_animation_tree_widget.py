import os

from PyQt5.QtCore import QMimeData
from PyQt5.QtCore import QPoint
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import QAbstractItemView
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtWidgets import QMenu
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QTreeWidget
from PyQt5.QtWidgets import QTreeWidgetItem


class AnimationTreeWidget(QTreeWidget):
    def __init__(self, animation_root, parent=None):
        super().__init__(parent)
        self.animation_root = animation_root
        self.setHeaderLabel("Animations")
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def show_context_menu(self, pos: QPoint):
        item = self.itemAt(pos)
        if item is None or item.parent() is None:
            return

        parent_text = item.parent().text(0)
        if parent_text not in {"frames", "if", "switch"}:
            return

        menu = QMenu(self)
        rename_action = menu.addAction("Rename")
        action = menu.exec_(self.viewport().mapToGlobal(pos))

        if action == rename_action:
            old_name = item.text(0)
            new_name, ok = QInputDialog.getText(self, "Rename", f"Rename {parent_text} '{old_name}' to:")
            if ok and new_name and new_name != old_name:
                success = self.rename_yaml_file(parent_text, old_name, new_name, item)
                if success:
                    item.setText(0, new_name)

    def rename_yaml_file(self, category, old_name, new_name, item_widget):
        # アニメーション名（ルートノード）
        animation_item = item_widget
        while animation_item.parent():
            animation_item = animation_item.parent()
        animation_name = animation_item.text(0)

        base_dir = self.animation_root

        # 対象ディレクトリ決定
        if category == "frames":
            dir_path = os.path.join(base_dir, animation_name, "frames")
        elif category == "if":
            dir_path = os.path.join(base_dir, animation_name, "conditions", "if")
        elif category == "switch":
            dir_path = os.path.join(base_dir, animation_name, "conditions", "switch")
        else:
            return False

        old_path = os.path.join(dir_path, f"{old_name}.yaml")
        new_path = os.path.join(dir_path, f"{new_name}.yaml")

        if os.path.exists(new_path):
            QMessageBox.warning(self, "Error", f"'{new_name}.yaml' already exists.")
            return False

        try:
            os.rename(old_path, new_path)
        except Exception as e:
            QMessageBox.critical(self, "Rename Failed", str(e))
            return False

        # MotionEditorWidget を取得
        editor = self
        while editor and not hasattr(editor, "scene"):
            editor = editor.parent()
        if not editor:
            QMessageBox.critical(self, "Error", "MotionEditorWidget not found.")
            return False

        # layout 修正処理
        layout = editor.scene.save_layout_yaml()
        singular_type = category.rstrip("s")
        updated = False

        # 新しい block を格納する dict
        new_block = {}
        rename_map = {}

        for block_key, block_data in layout.get("block", {}).items():
            info = block_data.get("info", {})
            block_type = info.get("type")
            block_filename = info.get("filename")
            block_id = info.get("id")

            if block_type == singular_type and block_filename == old_name:
                # info.filename 修正
                info["filename"] = new_name

                # block名を修正（例: frame_1_oldname → frame_1_newname）
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

        layout["block"] = new_block

        # target 修正（target: frame_1_oldname → frame_1_newname）
        for block_data in layout["block"].values():
            output = block_data.get("connection", {}).get("output", {})
            for conn in output.values():
                if isinstance(conn, dict) and "target" in conn:
                    old_target = conn["target"]
                    if old_target in rename_map:
                        conn["target"] = rename_map[old_target]
                        updated = True

        if updated:
            editor.scene.load_layout_yaml(layout)
            editor.save_current_animation()

        return True

    def mouseMoveEvent(self, event):
        item = self.currentItem()
        if item is None:
            event.ignore()
            return
        elif item.text(0) == "offset" and item.parent():
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
