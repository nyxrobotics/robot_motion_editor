import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QGraphicsView
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QSplitter
from PyQt5.QtWidgets import QTreeWidgetItem
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget

from ..logic.animation_file_manager import load_animation_file
from ..logic.animation_file_manager import save_animation_file
from .motion_editor_animation_tree_widget import AnimationTreeWidget
from .motion_editor_scene import FrameBlockItem
from .motion_editor_scene import MotionFlowScene


class MotionEditorWidget(QWidget):
    def __init__(self, animation_root="."):
        super().__init__()
        self.animation_root = animation_root
        self.animation_tree = AnimationTreeWidget()
        self.current_animation_name = None
        self.init_ui()
        self.load_animation_list()

    def init_ui(self):
        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_panel = QVBoxLayout(left_widget)
        self.save_anim_btn = QPushButton("Save Animation")
        self.save_frame_btn = QPushButton("Save Frame")
        self.new_anim_btn = QPushButton("New Animation")
        self.new_frame_btn = QPushButton("New Frame")
        self.delete_anim_btn = QPushButton("Delete Animation")
        self.delete_frame_btn = QPushButton("Delete Frame")

        self.save_anim_btn.clicked.connect(self.save_current_animation)
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

        self.animation_tree.itemClicked.connect(self.on_tree_item_clicked)

        self.scene = MotionFlowScene()
        self.scene.setSceneRect(0, 0, 2000, 2000)
        self.view = QGraphicsView(self.scene)
        self.view.setAcceptDrops(True)
        self.view.setRenderHints(self.view.renderHints() | QPainter.Antialiasing)

        splitter.addWidget(left_widget)
        splitter.addWidget(self.view)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        layout = QVBoxLayout()
        layout.addWidget(splitter)
        self.setLayout(layout)

    def on_tree_item_clicked(self, item):
        animation_item = item if item.parent() is None else item.parent()
        name = animation_item.text(0)
        if name == self.current_animation_name:
            return
        self.load_animation_by_name(name)

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

    def load_animation_by_name(self, animation_name):
        self.current_animation_name = animation_name
        result = load_animation_file(self.animation_root, animation_name)
        layout = result.get("layout", {})
        self.scene.load_layout_dict(layout)

    def save_current_animation(self):
        if not self.current_animation_name:
            QMessageBox.information(self, "Save", "No animation selected to save.")
            return

        layout = self.scene.to_layout_dict()
        print("[DEBUG] Final layout from scene:", layout)
        save_animation_file(self.animation_root, self.current_animation_name, layout)
        print("Saved:", self.current_animation_name)

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
            f.write("  # animation flowchart\n")
        with open(os.path.join(animation_path, "frames", "initial_frame.yaml"), "w") as f:
            f.write("  # initial frame\n")

        self.load_animation_list()
        self.load_animation_by_name(name)

    def create_new_frame(self):
        current_item = self.animation_tree.currentItem()
        if not current_item:
            QMessageBox.information(self, "Selection Error", "Please select an animation.")
            return

        animation_item = current_item.parent() if current_item.parent() else current_item
        animation_name = animation_item.text(0)
        frames_dir = os.path.join(self.animation_root, animation_name, "frames")

        name, ok = QInputDialog.getText(self, "New Frame", "Enter frame name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        frame_path = os.path.join(frames_dir, f"{name}.yaml")
        if os.path.exists(frame_path):
            QMessageBox.warning(self, "Name Conflict", f"Frame '{name}' already exists.")
            return

        with open(frame_path, "w") as f:
            f.write("  # frame content\n")

        self.load_animation_list()
        self.load_animation_by_name(animation_name)

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
            self.current_animation_name = None

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
            self.load_animation_by_name(anim_name)
