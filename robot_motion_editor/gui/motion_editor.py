# motion_editor.py
import os

from PyQt5.QtCore import QMimeData
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDrag
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QGraphicsView
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QTreeWidgetItem
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget

from .motion_editor_animation_tree_widget import AnimationTreeWidget
from .motion_editor_scene import FrameBlockItem
from .motion_editor_scene import MotionFlowScene


class MotionEditorWidget(QWidget):
    def __init__(self, animation_root="."):
        super().__init__()
        self.animation_root = animation_root
        self.animation_tree = AnimationTreeWidget()
        self.animation_tree.itemDoubleClicked.connect(self.on_animation_double_clicked)

        self.init_ui()
        self.load_animation_list()

    def init_ui(self):
        main_layout = QHBoxLayout()

        # --- Left Panel ---
        left_panel = QVBoxLayout()
        self.save_anim_btn = QPushButton("Save Animation")
        self.save_frame_btn = QPushButton("Save Frame")
        self.new_anim_btn = QPushButton("New Animation")
        self.new_frame_btn = QPushButton("New Frame")
        self.delete_anim_btn = QPushButton("Delete Animation")
        self.delete_frame_btn = QPushButton("Delete Frame")

        self.save_anim_btn.clicked.connect(lambda: print("Save Animation not implemented"))
        self.save_frame_btn.clicked.connect(lambda: print("Save Frame not implemented"))
        self.new_anim_btn.clicked.connect(self.create_new_animation)
        self.new_frame_btn.clicked.connect(self.create_new_frame)
        self.delete_anim_btn.clicked.connect(self.delete_animation)
        self.delete_frame_btn.clicked.connect(self.delete_frame)

        left_panel.addWidget(QLabel("Animation List"))
        for btn in [self.save_anim_btn, self.save_frame_btn, self.new_anim_btn, self.new_frame_btn,
                    self.delete_anim_btn, self.delete_frame_btn]:
            left_panel.addWidget(btn)
        left_panel.addWidget(self.animation_tree)

        # --- Right Panel (Flowchart) ---
        self.scene = MotionFlowScene()
        self.scene.setSceneRect(0, 0, 2000, 2000)
        self.view = QGraphicsView(self.scene)
        self.view.setAcceptDrops(True)
        self.view.setRenderHints(self.view.renderHints() | QPainter.Antialiasing)

        main_layout.addLayout(left_panel, stretch=1)
        main_layout.addWidget(self.view, stretch=3)
        self.setLayout(main_layout)

    def load_animation_list(self):
        self.animation_tree.clear()
        if not os.path.isdir(self.animation_root):
            return

        for animation_name in sorted(os.listdir(self.animation_root)):
            animation_dir = os.path.join(self.animation_root, animation_name)
            if not os.path.isdir(animation_dir):
                continue

            animation_item = QTreeWidgetItem([animation_name])
            frames_dir = os.path.join(animation_dir, "frames")
            if os.path.isdir(frames_dir):
                for frame_name in sorted(os.listdir(frames_dir)):
                    if frame_name.endswith(".yaml"):
                        QTreeWidgetItem(animation_item, [frame_name.replace(".yaml", "")])
            self.animation_tree.addTopLevelItem(animation_item)

    def create_new_animation(self):
        name, ok = QInputDialog.getText(self, "New Animation", "Enter animation name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        animation_path = os.path.join(self.animation_root, name)
        if os.path.exists(animation_path):
            QMessageBox.warning(self, "Name Conflict", f"Animation '{name}' already exists.")
            return

        os.makedirs(os.path.join(animation_path, "frames"), exist_ok=True)
        with open(os.path.join(animation_path, f"{name}.yaml"), "w") as f:
            f.write("nodes:\n")
        with open(os.path.join(animation_path, "frames", "initial_frame.yaml"), "w") as f:
            f.write("# initial frame\n")

        self.load_animation_list()

    def create_new_frame(self):
        current_item = self.animation_tree.currentItem()
        if not current_item:
            QMessageBox.information(self, "Selection Error", "Please select an animation.")
            return

        if current_item.parent():
            animation_item = current_item.parent()
        else:
            animation_item = current_item

        animation_name = animation_item.text(0)
        animation_path = os.path.join(self.animation_root, animation_name)
        frames_dir = os.path.join(animation_path, "frames")

        name, ok = QInputDialog.getText(self, "New Frame", "Enter frame name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        frame_path = os.path.join(frames_dir, f"{name}.yaml")
        if os.path.exists(frame_path):
            QMessageBox.warning(self, "Name Conflict", f"Frame '{name}' already exists.")
            return

        with open(frame_path, "w") as f:
            f.write("# frame content\n")

        self.load_animation_list()

    def delete_animation(self):
        item = self.animation_tree.currentItem()
        if not item or item.parent() is not None:
            QMessageBox.warning(self, "Selection Error", "Please select an animation to delete.")
            return
        name = item.text(0)
        path = os.path.join(self.animation_root, name)

        reply = QMessageBox.question(self, "Delete Animation",
                                     f"Are you sure you want to delete animation '{name}'?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            import shutil
            shutil.rmtree(path, ignore_errors=True)
            self.load_animation_list()

    def delete_frame(self):
        item = self.animation_tree.currentItem()
        parent = item.parent() if item else None
        if not item or not parent:
            QMessageBox.warning(self, "Selection Error", "Please select a frame to delete.")
            return

        anim_name = parent.text(0)
        frame_name = item.text(0)
        path = os.path.join(self.animation_root, anim_name, "frames", f"{frame_name}.yaml")

        reply = QMessageBox.question(self, "Delete Frame",
                                     f"Are you sure you want to delete frame '{frame_name}'?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if os.path.exists(path):
                os.remove(path)
            self.load_animation_list()

    def on_animation_double_clicked(self, item, column):
        if item.parent() is not None:
            return  # only respond to animation nodes

        name = item.text(0)
        path = os.path.join(self.animation_root, name, f"{name}.yaml")
        if os.path.exists(path):
            self.scene.clear()
            try:
                with open(path, "r") as f:
                    import yaml
                    data = yaml.safe_load(f) or {}
                    for node in data.get("nodes", []):
                        frame = node.get("frame")
                        x = node.get("x", 0)
                        y = node.get("y", 0)
                        block = FrameBlockItem(frame)
                        block.setPos(x, y)
                        self.scene.addItem(block)
            except Exception as e:
                print(f"Failed to load flowchart: {e}")
