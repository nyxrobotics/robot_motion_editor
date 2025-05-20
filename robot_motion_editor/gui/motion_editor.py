import math
import os

import rospy
import yaml
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
from sensor_msgs.msg import JointState

from ..logic.animation_file_manager import load_animation_file
from ..logic.animation_file_manager import save_animation_file
from ..logic.initial_pose_file_manager import load_initial_pose
from ..logic.initial_pose_file_manager import save_initial_pose
from ..visualizer.animation_previwe_visualizer import AnimationPreviewVisualizer
from ..visualizer.trajectory_visualizer import TrajectoryVisualizer
from .animation_preview_button_widget import AnimationPreviewButtonWidget
from .frame_editor import FrameEditorDialog
from .if_condition_editor import IfConditionEditorDialog
from .motion_editor_animation_tree_widget import AnimationTreeWidget
from .motion_editor_scene import FrameBlockItem
from .motion_editor_scene import MotionFlowScene
from .motion_graphics_view import MotionGraphicsView
from .offset_editor import OffsetEditorDialog
from .switch_condition_editor import SwitchConditionEditorDialog


class MotionEditorWidget(QWidget):
    def __init__(self, motion_directory=".", joint_names=None, joint_limits=None,
                 available_variables=None, trajectory_visualizer: TrajectoryVisualizer = None):
        super().__init__()
        self.motion_directory = motion_directory
        self.joint_names = joint_names or []
        self.joint_limits = joint_limits or {}
        self.available_variables = available_variables or []
        self.trajectory_visualizer = trajectory_visualizer
        self.current_animation_name = None
        self.initial_joint_state = None

        self.animation_tree = AnimationTreeWidget(motion_directory=self.motion_directory, parent=self)
        self.scene = MotionFlowScene(editor_widget=self)
        self.view = MotionGraphicsView(self.scene)

        self.preview_controller = AnimationPreviewVisualizer(
            scene=self.scene,
            trajectory_visualizer=self.trajectory_visualizer,
            frame_loader=lambda name: self.load_joint_state_and_durations(self.resolve_frame_path(name)),
            initial_joint_state=self.initial_joint_state
        )

        self.init_ui()
        self.load_animation_list()

    def resolve_frame_path(self, frame_name):
        return os.path.join(
            self.motion_directory,
            self.current_animation_name,
            "frames",
            f"{frame_name}.yaml"
        )

    def load_animation_by_name(self, animation_name):
        if not self.confirm_save_if_unsaved_changes():
            return
        self.current_animation_name = animation_name
        layout = load_animation_file(self.motion_directory, animation_name)
        self.scene.load_layout_yaml(layout)
        self.scene.highlight_preview_path()

        # 初期姿勢読み込み（initial_frame）
        try:
            self.initial_joint_state, _, _ = self.load_joint_state_and_durations(
                self.resolve_frame_path("initial_frame")
            )
            self.preview_controller.initial_joint_state = self.initial_joint_state
        except Exception as e:
            rospy.logwarn(f"[MotionEditor] Failed to load initial_frame: {e}")

    def init_ui(self):
        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # プレビューボタンを縦に並べて配置
        self.preview_buttons = AnimationPreviewButtonWidget(self.preview_controller)
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

        for btn in [self.save_anim_btn, self.new_anim_btn, self.new_frame_btn,
                    self.delete_anim_btn, self.delete_frame_btn]:
            left_layout.addWidget(btn)

        left_layout.addWidget(QLabel("Animation List"))
        left_layout.addWidget(self.animation_tree)

        self.save_anim_btn.clicked.connect(self.save_current_animation)
        self.new_anim_btn.clicked.connect(self.create_new_animation)
        self.new_frame_btn.clicked.connect(self.create_new_frame)
        self.delete_anim_btn.clicked.connect(self.delete_animation)
        self.delete_frame_btn.clicked.connect(self.delete_frame)
        self.animation_tree.itemClicked.connect(self.on_tree_item_clicked)
        self.animation_tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)

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
        # Get the top animation name from any hierarchy
        animation_item = item
        while animation_item.parent() is not None:
            animation_item = animation_item.parent()

        name = animation_item.text(0)
        # Do nothing if the animation is already selected
        if name == self.current_animation_name:
            return

        self.load_animation_by_name(name)

    def on_tree_item_double_clicked(self, item):
        if item.text(0) == "offset":
            animation_item = item
            while animation_item.parent() is not None:
                animation_item = animation_item.parent()
            animation_name = animation_item.text(0)
            self.open_offset_editor()

        elif item.parent() and item.parent().text(0) == "frames":
            animation_item = item
            while animation_item.parent() is not None:
                animation_item = animation_item.parent()
            animation_name = animation_item.text(0)
            frame_name = item.text(0)

            frame_path = os.path.join(self.motion_directory, animation_name, "frames", f"{frame_name}.yaml")
            if not os.path.exists(frame_path):
                QMessageBox.warning(self, "Missing File", f"{frame_path} not found.")
                return

            dlg = FrameEditorDialog(
                joint_names=self.joint_names,
                joint_limits=self.joint_limits,
                available_variables=self.available_variables,
                frame_path=frame_path,
                trajectory_visualizer=self.trajectory_visualizer
            )
            current_state, move, wait = self.load_joint_state_and_durations(frame_path)
            dlg.frame_visualizer.set_current_frame(current_state, move, wait)

            if hasattr(self, "initial_joint_state"):
                dlg.frame_visualizer.set_initial_frame(self.initial_joint_state)

            # in/out は接続されていないため current をそのまま使用
            dlg.frame_visualizer.set_in_frame(current_state, move, wait)
            dlg.frame_visualizer.set_out_frame(current_state, move, wait)
            dlg.exec_()

        elif item.parent() and item.parent().text(0) == "if":
            animation_item = item
            while animation_item.parent() is not None:
                animation_item = animation_item.parent()
            animation_name = animation_item.text(0)
            condition_name = item.text(0)

            condition_path = os.path.join(
                self.motion_directory, animation_name, "conditions", "if", f"{condition_name}.yaml"
            )
            if not os.path.exists(condition_path):
                QMessageBox.warning(self, "Missing File", f"{condition_path} not found.")
                return

            dlg = IfConditionEditorDialog(
                available_variables=self.available_variables,
                condition_path=condition_path
            )
            dlg.exec_()

        elif item.parent() and item.parent().text(0) == "switch":
            animation_item = item
            while animation_item.parent() is not None:
                animation_item = animation_item.parent()
            animation_name = animation_item.text(0)
            condition_name = item.text(0)

            condition_path = os.path.join(
                self.motion_directory, animation_name, "conditions", "switch", f"{condition_name}.yaml"
            )
            if not os.path.exists(condition_path):
                QMessageBox.warning(self, "Missing File", f"{condition_path} not found.")
                return

            dlg = SwitchConditionEditorDialog(
                condition_path=condition_path,
                available_variables=self.available_variables
            )
            if dlg.exec_():
                if dlg.result:
                    new_num_cases = dlg.result.get("num_cases", 2)
                    self.scene.update_switch_block(condition_name, new_num_cases)

    def load_animation_list(self):
        self.animation_tree.clear()
        if not os.path.isdir(self.motion_directory):
            return

        for animation_name in sorted(os.listdir(self.motion_directory)):
            animation_dir = os.path.join(self.motion_directory, animation_name)
            if not os.path.isdir(animation_dir):
                continue

            anim_item = QTreeWidgetItem([animation_name])
            self.animation_tree.addTopLevelItem(anim_item)

            # Edit initial offset for the frames
            QTreeWidgetItem(anim_item, ["offset"])

            # frames
            frames_dir = os.path.join(animation_dir, "frames")
            frames_item = QTreeWidgetItem(anim_item, ["frames"])
            if os.path.isdir(frames_dir):
                for fname in sorted(os.listdir(frames_dir)):
                    if fname.lower().endswith(".yaml"):
                        QTreeWidgetItem(frames_item, [fname[:-5]])

            # conditions
            conditions_dir = os.path.join(animation_dir, "conditions")
            conditions_item = QTreeWidgetItem(anim_item, ["conditions"])

            # if
            if_dir = os.path.join(conditions_dir, "if")
            if_item = QTreeWidgetItem(conditions_item, ["if"])
            if os.path.isdir(if_dir):
                for fname in sorted(os.listdir(if_dir)):
                    if fname.lower().endswith(".yaml"):
                        QTreeWidgetItem(if_item, [fname[:-5]])

            # switch
            switch_dir = os.path.join(conditions_dir, "switch")
            switch_item = QTreeWidgetItem(conditions_item, ["switch"])
            if os.path.isdir(switch_dir):
                for fname in sorted(os.listdir(switch_dir)):
                    if fname.lower().endswith(".yaml"):
                        QTreeWidgetItem(switch_item, [fname[:-5]])

    def load_animation_by_name(self, animation_name):
        if animation_name == self.current_animation_name:
            return
        if not self.confirm_save_if_unsaved_changes():
            return
        self.current_animation_name = animation_name
        layout = load_animation_file(self.motion_directory, animation_name)
        self.scene.load_layout_yaml(layout)
        self.scene.highlight_preview_path()

    def save_current_animation(self):
        if not self.current_animation_name:
            QMessageBox.information(self, "Save", "No animation selected to save.")
            return
        layout = self.scene.save_layout_yaml()
        save_animation_file(self.motion_directory, self.current_animation_name, layout)

    def create_new_animation(self):
        name, ok = QInputDialog.getText(self, "New Animation", "Enter animation name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        animation_path = os.path.join(self.motion_directory, name)
        if os.path.exists(animation_path):
            QMessageBox.warning(self, "Name Conflict", f"Animation '{name}' already exists.")
            return
        os.makedirs(os.path.join(animation_path, "frames"), exist_ok=True)
        with open(os.path.join(animation_path, f"{name}.yaml"), "w") as f:
            f.write("  # animation flowchart")
        with open(os.path.join(animation_path, "offset.yaml"), "w") as f:
            f.write("  # initial frame offset")
        self.load_animation_list()
        self.load_animation_by_name(name)

    def create_new_frame(self):
        # ...省略（通常のframe追加処理）...
        if not current_item:
            QMessageBox.information(self, "Selection Error", "Please select an animation.")
            return

        animation_item = current_item.parent() if current_item.parent() else current_item
        animation_name = animation_item.text(0)
        frames_dir = os.path.join(self.motion_directory, animation_name, "frames")

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
        path = os.path.join(self.motion_directory, name)

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
        path = os.path.join(self.motion_directory, anim_name, "frames", f"{frame_name}.yaml")

        reply = QMessageBox.question(self, "Delete Frame",
                                     f"Are you sure you want to delete frame '{frame_name}'?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if os.path.exists(path):
                os.remove(path)
            self.load_animation_list()
            self.load_animation_by_name(anim_name)

    def open_offset_editor(self):
        offset_path = os.path.join(self.motion_directory, self.current_animation_name, "offset.yaml")

        dlg = OffsetEditorDialog(
            joint_names=self.joint_names,
            joint_limits=self.joint_limits,
            available_variables=self.available_variables,
            offset_path=offset_path
        )

        if dlg.exec_():
            updated_data = dlg.get_joint_data()
            save_initial_pose(
                os.path.join(self.motion_directory, self.current_animation_name),
                joint_names=list(updated_data.keys()),
                positions=[v["position"] for v in updated_data.values()],
                enabled={k: v["enable"] for k, v in updated_data.items()},
                pid_config={k: v["pid"] for k, v in updated_data.items()},
                feedback_exprs={k: v["feedback"] for k, v in updated_data.items()},
                filename="offset.yaml"
            )

    def load_joint_state_and_durations(self, path):
        move_duration = 1.0
        wait_duration = 0.0
        msg = JointState()
        msg.name = []
        msg.position = []

        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            print(f"[WARN] Failed to load {path}: {e}")
            return msg, move_duration, wait_duration

        if not data:
            print(f"[WARN] Empty or invalid YAML in {path}")
            return msg, move_duration, wait_duration
        joints_data = data.get("joints", {})
        for name, joint_info in joints_data.items():
            pos = joint_info.get("position") if isinstance(joint_info, dict) else joint_info
            if pos is not None:
                msg.name.append(name)
                msg.position.append(pos)

        msg.header.stamp = rospy.Time.now()
        move_duration = data.get("time", {}).get("move_duration", move_duration)
        wait_duration = data.get("time", {}).get("wait_duration", wait_duration)

        return msg, move_duration, wait_duration

    def open_frame_file_editor(self, frame_name):
        frame_path = os.path.join(self.motion_directory, self.current_animation_name, "frames", f"{frame_name}.yaml")
        dlg = FrameEditorDialog(
            joint_names=self.joint_names,
            joint_limits=self.joint_limits,
            available_variables=self.available_variables,
            frame_path=frame_path
        )
        dlg.exec_()

    def open_frame_block_editor(self, block_id: str):
        block = self.scene.block_objects.get(block_id)
        if not block:
            print(f"[WARN] No block found for id: {block_id}")
            return

        frame_path = os.path.join(
            self.motion_directory,
            self.current_animation_name,
            "frames",
            f"{block.filename}.yaml")
        dlg = FrameEditorDialog(
            joint_names=self.joint_names,
            joint_limits=self.joint_limits,
            available_variables=self.available_variables,
            frame_path=frame_path,
            parent=self,
            trajectory_visualizer=self.trajectory_visualizer
        )

        if hasattr(dlg, "frame_visualizer"):
            current_state, current_move, current_wait = self.load_joint_state_and_durations(frame_path)
            dlg.frame_visualizer.set_current_frame(current_state, current_move, current_wait)

            if hasattr(self, "initial_joint_state"):
                dlg.frame_visualizer.set_initial_frame(self.initial_joint_state)

            in_block = self.scene.find_previous_frame_block(block)
            if in_block and in_block.filename:
                in_path = os.path.join(
                    self.motion_directory,
                    self.current_animation_name,
                    "frames",
                    f"{in_block.filename}.yaml"
                )
                in_state, in_move, in_wait = self.load_joint_state_and_durations(in_path)
                dlg.frame_visualizer.set_in_frame(in_state, in_move, in_wait)

            out_block = self.scene.find_next_frame_block(block)
            if out_block and out_block.filename:
                out_path = os.path.join(
                    self.motion_directory,
                    self.current_animation_name,
                    "frames",
                    f"{out_block.filename}.yaml"
                )
                out_state, out_move, out_wait = self.load_joint_state_and_durations(out_path)
                dlg.frame_visualizer.set_out_frame(out_state, out_move, out_wait)

        dlg.exec_()

    def open_if_condition_editor(self, condition_name):
        condition_path = os.path.join(
            self.motion_directory,
            self.current_animation_name,
            "conditions",
            "if",
            f"{condition_name}.yaml")
        dlg = IfConditionEditorDialog(
            available_variables=self.available_variables,
            condition_path=condition_path
        )
        dlg.exec_()

    def open_switch_condition_editor(self, condition_name):
        condition_path = os.path.join(
            self.motion_directory,
            self.current_animation_name,
            "conditions", "switch", f"{condition_name}.yaml"
        )
        dlg = SwitchConditionEditorDialog(
            condition_path=condition_path,
            available_variables=self.available_variables
        )

        if dlg.exec_():
            if dlg.result:
                new_num_cases = dlg.result.get("num_cases", 2)
                # フローチャート上のブロックを更新
                self.scene.update_switch_block(condition_name, new_num_cases)

    def confirm_save_if_unsaved_changes(self):
        if not self.current_animation_name:
            return True

        current_layout = self.scene.save_layout_yaml()
        saved_layout = load_animation_file(self.motion_directory, self.current_animation_name)

        if current_layout == saved_layout:
            return True

        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            f"Animation '{self.current_animation_name}' has unsaved changes.\nDo you want to save them?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
        )

        if reply == QMessageBox.Save:
            self.save_current_animation()
            return True
        elif reply == QMessageBox.Discard:
            return True
        else:
            return False
