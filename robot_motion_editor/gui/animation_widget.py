import os
import shutil

import rospy
import yaml
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QSplitter
from PyQt5.QtWidgets import QTreeWidgetItem
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget

from ..logic.animation_file_manager import AnimationData
from ..logic.frame_file_manager import FrameData
from ..logic.frame_file_manager import FrameFileManager
from ..logic.joint_data_manager import JointDataManager
from ..logic.motion_directory_manager import MotionDirectoryManager
from ..robot_interface.animation_commander import AnimationCommander
from ..robot_interface.trajectory_commander import TrajectoryCommander
from ..visualizer.animation_visualizer import AnimationVisualizer
from ..visualizer.trajectory_visualizer import TrajectoryVisualizer
from .animation_editor_widget import AnimationEditorWidget
from .animation_file_widget import AnimationFileWidget
from .animation_graphics_view import AnimatioGraphicsView
from .animation_preview_button_widget import AnimationPreviewButtonWidget
from .frame_editor import FrameEditorDialog
from .if_condition_editor import IfConditionEditorDialog
from .initial_frame_editor import InitialFrameEditorDialog
from .switch_condition_editor import SwitchConditionEditorDialog


class AnimaitonWidget(QWidget):
    def __init__(
            self,
            motion_directory_manager: MotionDirectoryManager,
            joint_data_manager: JointDataManager,
            trajectory_visualizer: TrajectoryVisualizer = None,
            trajectory_commander: TrajectoryCommander = None):
        super().__init__()
        self.motion_directory_manager = motion_directory_manager
        self.joint_data_manager = joint_data_manager
        self.trajectory_visualizer = trajectory_visualizer
        self.trajectory_commander = trajectory_commander

        self.animation_tree = AnimationFileWidget(motion_directory_manager=self.motion_directory_manager, parent=self)
        self.animation_flow_scene = AnimationEditorWidget(motion_directory_manager=self.motion_directory_manager)
        self.animation_flow_scene.editor_widget = self
        self.view = AnimatioGraphicsView(self.animation_flow_scene)

        self.animation_visualizer = AnimationVisualizer(
            animation_flow_scene=self.animation_flow_scene,
            trajectory_visualizer=self.trajectory_visualizer,
            motion_directory_manager=self.motion_directory_manager,
            joint_data_manager=self.joint_data_manager)
        self.animation_commander = AnimationCommander(
            trajectory_commander=self.trajectory_commander,
            animation_flow_scene=self.animation_flow_scene,
            motion_directory_manager=self.motion_directory_manager,
            joint_data_manager=self.joint_data_manager)
        self.init_ui()
        self.reload_animation_tree()
        self.open_editors = {}  # e.g. {"initial_frame": dlg, "frame:walk1": dlg}

    def init_ui(self):
        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        self.preview_buttons = AnimationPreviewButtonWidget(
            animation_visualizer=self.animation_visualizer,
            animation_commander=self.animation_commander)
        preview_layout = QVBoxLayout()
        preview_layout.addWidget(self.preview_buttons.play_btn)
        preview_layout.addWidget(self.preview_buttons.pause_btn)
        preview_layout.addWidget(self.preview_buttons.stop_btn)
        left_layout.addLayout(preview_layout)

        self.save_anim_btn = QPushButton("Save Animation")
        self.new_anim_btn = QPushButton("New Animation")
        self.new_frame_btn = QPushButton("New Frame")
        self.delete_anim_btn = QPushButton("Delete Animation")
        self.delete_frame_btn = QPushButton("Delete Frame")

        for btn in [
                self.save_anim_btn,
                self.new_anim_btn,
                self.new_frame_btn,
                self.delete_anim_btn,
                self.delete_frame_btn]:
            left_layout.addWidget(btn)

        left_layout.addWidget(QLabel("Animation List"))
        left_layout.addWidget(self.animation_tree)

        self.save_anim_btn.clicked.connect(self.save_current_animation)
        self.new_anim_btn.clicked.connect(self.create_new_animation)
        self.new_frame_btn.clicked.connect(self.create_new_frame)
        self.delete_anim_btn.clicked.connect(self.delete_animation)
        self.delete_frame_btn.clicked.connect(self.delete_frame)
        self.animation_tree.itemClicked.connect(self.on_tree_item_clicked)
        self.animation_tree.itemDoubleClickedSignal.connect(self.on_tree_item_double_clicked)

        self.view.setAcceptDrops(True)
        self.view.setRenderHints(self.view.renderHints() | QPainter.Antialiasing)

        splitter.addWidget(left_widget)
        splitter.addWidget(self.view)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        layout = QVBoxLayout()
        layout.addWidget(splitter)
        self.setLayout(layout)

    def load_animation_by_name(self, animation_name):
        if not self.confirm_save_if_unsaved_changes():
            return

        self.motion_directory_manager.set_current_animation(animation_name)

        anim_data = AnimationData()
        anim_data.load_from_file(self.motion_directory_manager.resolve_animation_yaml_path())
        self.animation_flow_scene.set_animation_data(anim_data)
        self.animation_flow_scene.highlight_preview_path()

        try:
            frame_data = FrameData(joint_names=self.joint_data_manager.get_joint_names())
            frame_data.load_from_file(self.motion_directory_manager.resolve_initial_frame_path())
            self.initial_joint_state = frame_data.get_joint_state()
            self.animation_visualizer.initial_joint_state = self.initial_joint_state
        except Exception as e:
            rospy.logwarn(f"[MotionEditor] Failed to load initial_frame: {e}")

    def reload_animation_tree(self):
        """Reload the full animation tree with all children."""
        self.reload_animation_list()
        for i in range(self.animation_tree.topLevelItemCount()):
            animation_name = self.animation_tree.topLevelItem(i).text(0)
            self.reload_animation_contents(animation_name)
        self.animation_tree.setCurrentItem(None)

    def reload_animation_list(self):
        """Update only the top-level animation names in the tree."""
        self.animation_tree.clear()
        base_dir = self.motion_directory_manager.get_motion_directory()
        if not os.path.isdir(base_dir):
            return

        for animation_name in sorted(os.listdir(base_dir)):
            animation_path = os.path.join(base_dir, animation_name)
            if os.path.isdir(animation_path):
                anim_item = QTreeWidgetItem([animation_name])
                self.animation_tree.addTopLevelItem(anim_item)

    def reload_animation_contents(self, animation_name: str):
        """Update the contents of a specific animation node (initial_frame, frames, conditions)."""
        base_dir = self.motion_directory_manager.get_motion_directory()
        anim_path = os.path.join(base_dir, animation_name)
        if not os.path.isdir(anim_path):
            return

        # Find or create parent item
        for i in range(self.animation_tree.topLevelItemCount()):
            if self.animation_tree.topLevelItem(i).text(0) == animation_name:
                parent_item = self.animation_tree.topLevelItem(i)
                parent_item.takeChildren()
                break
        else:
            parent_item = QTreeWidgetItem([animation_name])
            self.animation_tree.addTopLevelItem(parent_item)

        # initial_frame
        QTreeWidgetItem(parent_item, ["initial_frame"])

        # frames
        frames_item = QTreeWidgetItem(parent_item, ["frames"])
        self.motion_directory_manager.set_current_animation(animation_name)
        for frame in self.motion_directory_manager.list_frame_files():
            QTreeWidgetItem(frames_item, [frame])

        # conditions
        conditions_item = QTreeWidgetItem(parent_item, ["conditions"])
        if_item = QTreeWidgetItem(conditions_item, ["if"])
        for cond in self.motion_directory_manager.list_if_condition_files():
            QTreeWidgetItem(if_item, [cond])
        switch_item = QTreeWidgetItem(conditions_item, ["switch"])
        for cond in self.motion_directory_manager.list_switch_condition_files():
            QTreeWidgetItem(switch_item, [cond])

        self.motion_directory_manager.set_current_animation(None)

    def save_current_animation(self):
        anim_name = self.motion_directory_manager.get_current_animation()
        if not anim_name:
            QMessageBox.information(self, "Save", "No animation selected to save.")
            return
        anim_data = self.animation_flow_scene.get_animation_data()
        anim_data.save_to_file(self.motion_directory_manager.resolve_animation_yaml_path())

    def confirm_save_if_unsaved_changes(self):
        anim_name = self.motion_directory_manager.get_current_animation()
        if not anim_name:
            return True

        current_data = self.animation_flow_scene.get_animation_data().get_dict()
        tmp_data = AnimationData()
        tmp_data.load_from_file(self.motion_directory_manager.resolve_animation_yaml_path())
        saved_data = tmp_data.get_dict()

        if current_data == saved_data:
            return True

        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            f"Animation '{anim_name}' has unsaved changes.\nDo you want to save them?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)

        if reply == QMessageBox.Save:
            self.save_current_animation()
            return True
        elif reply == QMessageBox.Discard:
            return True
        else:
            return False

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

        self.reload_animation_list()
        self.reload_animation_contents(name)
        self.load_animation_by_name(name)

    def create_new_frame(self):
        item = self.animation_tree.currentItem()
        if not item:
            QMessageBox.information(self, "Selection Error", "Please select an animation.")
            return

        animation_item = item
        while animation_item.parent():
            animation_item = animation_item.parent()
        animation_name = animation_item.text(0)

        self.motion_directory_manager.set_current_animation(animation_name)

        name, ok = QInputDialog.getText(self, "New Frame", "Enter frame name:")
        if not ok or not name.strip():
            return
        name = name.strip()

        frame_path = self.motion_directory_manager.resolve_frame_path(name)
        if os.path.exists(frame_path):
            QMessageBox.warning(self, "Name Conflict", f"Frame '{name}' already exists.")
            return

        default_frame_data = FrameData().get_dict()
        FrameFileManager.save_dict(frame_path, default_frame_data)

        self.reload_animation_contents(animation_name)
        self.load_animation_by_name(animation_name)

    def delete_animation(self):
        item = self.animation_tree.currentItem()
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
            self.reload_animation_list()

    def delete_frame(self):
        item = self.animation_tree.currentItem()
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
            self.load_animation_by_name(animation_name)

    def on_tree_item_clicked(self, item):
        animation_item = item
        while animation_item.parent():
            animation_item = animation_item.parent()
        name = animation_item.text(0)
        if name == self.motion_directory_manager.get_current_animation():
            return
        self.load_animation_by_name(name)

    def on_tree_item_double_clicked(self, item):
        animation_item = item
        while animation_item.parent():
            animation_item = animation_item.parent()
        animation_name = animation_item.text(0)
        self.motion_directory_manager.set_current_animation(animation_name)

        label = item.text(0)
        parent = item.parent().text(0) if item.parent() else ""

        if label == "initial_frame":
            self.open_editor_by_type("initial_frame")
        elif parent == "frames":
            self.open_editor_by_type("frame", label)
        elif parent == "if":
            self.open_editor_by_type("if", label)
        elif parent == "switch":
            self.open_editor_by_type("switch", label)

    def on_start_block_double_clicked(self):
        self.open_editor_by_type("initial_frame", "")

    def on_frame_block_double_clicked(self, filename: str):
        self.open_editor_by_type("frame", filename)

    def on_if_block_double_clicked(self, filename: str):
        self.open_editor_by_type("if", filename)

    def on_switch_block_double_clicked(self, filename: str):
        self.open_editor_by_type("switch", filename)

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
                frame_name=name,
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
