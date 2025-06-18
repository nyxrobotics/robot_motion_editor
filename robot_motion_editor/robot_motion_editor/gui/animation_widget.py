import rospy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QSplitter
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget

from ..logic.animation_file_manager import AnimationData
from ..logic.frame_file_manager import FrameData
from ..logic.joint_data_manager import JointDataManager
from ..logic.motion_file_manager import MotionFileManager
from ..robot_interface.animation_commander import AnimationCommander
from ..robot_interface.trajectory_commander import TrajectoryCommander
from ..visualizer.animation_visualizer import AnimationVisualizer
from ..visualizer.trajectory_visualizer import TrajectoryVisualizer
from .animation_editor_widget import AnimationEditorWidget
from .animation_file_widget import AnimationFileWidget
from .animation_graphics_view import AnimatioGraphicsView
from .animation_item_editor_launcher import AnimationItemEditorLauncher
from .animation_preview_button_widget import AnimationPreviewButtonWidget


class AnimaitonWidget(QWidget):
    def __init__(
            self,
            motion_file_manager: MotionFileManager,
            joint_data_manager: JointDataManager,
            trajectory_visualizer: TrajectoryVisualizer,
            trajectory_commander: TrajectoryCommander):
        super().__init__()
        self.motion_file_manager = motion_file_manager
        self.joint_data_manager = joint_data_manager
        self.trajectory_visualizer = trajectory_visualizer
        self.trajectory_commander = trajectory_commander

        self.editor_launcher = AnimationItemEditorLauncher(
            joint_data_manager=self.joint_data_manager,
            motion_file_manager=self.motion_file_manager,
            trajectory_visualizer=self.trajectory_visualizer,
            trajectory_commander=self.trajectory_commander,
        )
        self.animation_flow_scene = AnimationEditorWidget(
            motion_file_manager=self.motion_file_manager,
            editor_launcher=self.editor_launcher)
        self.view = AnimatioGraphicsView(self.animation_flow_scene)

        self.animation_tree = AnimationFileWidget(
            motion_file_manager=self.motion_file_manager,
            joint_data_manager=self.joint_data_manager,
            trajectory_visualizer=self.trajectory_visualizer,
            trajectory_commander=self.trajectory_commander,
            editor_launcher=self.editor_launcher,
            parent=self)
        self.animation_visualizer = AnimationVisualizer(
            animation_flow_scene=self.animation_flow_scene,
            trajectory_visualizer=self.trajectory_visualizer,
            motion_file_manager=self.motion_file_manager,
            joint_data_manager=self.joint_data_manager)
        self.animation_commander = AnimationCommander(
            trajectory_commander=self.trajectory_commander,
            animation_flow_scene=self.animation_flow_scene,
            motion_file_manager=self.motion_file_manager,
            joint_data_manager=self.joint_data_manager)
        self.init_ui()
        self.reload_animation_tree()

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

        self.save_anim_btn.clicked.connect(self.on_save_anim_btn)
        self.new_anim_btn.clicked.connect(self.on_new_animation_btn)
        self.new_frame_btn.clicked.connect(self.on_new_frame_btn)
        self.delete_anim_btn.clicked.connect(self.on_delete_anim_btn)
        self.delete_frame_btn.clicked.connect(self.on_delete_frame_btn)
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

    def reload_animation_tree(self):
        """Reload the full animation tree with all children."""
        self.animation_tree.reload_animation_list()
        for i in range(self.animation_tree.topLevelItemCount()):
            animation_name = self.animation_tree.topLevelItem(i).text(0)
            self.animation_tree.reload_file_lists(animation_name)
        self.motion_file_manager.set_animation_name(None)
        self.animation_tree.setCurrentItem(None)

    def on_save_anim_btn(self):
        anim_data = self.animation_flow_scene.get_animation_data()
        self.motion_file_manager.set_animation_data(anim_data)

    def confirm_save_if_unsaved_changes(self):
        rospy.loginfo("[MotionEditor] Checking for unsaved changes.")
        anim_name = self.motion_file_manager.get_animation_name()
        if not anim_name:
            return True

        current_data = self.animation_flow_scene.get_animation_data().get_dict()
        saved_data = self.motion_file_manager.get_animation_data().get_dict()

        if current_data == saved_data:
            return True

        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            f"Animation '{anim_name}' has unsaved changes.\nDo you want to save them?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)

        if reply == QMessageBox.Save:
            self.on_save_anim_btn()
            return True
        elif reply == QMessageBox.Discard:
            return True
        else:
            return False

    def on_new_animation_btn(self):
        name = self.animation_tree.create_new_animation()
        self.animation_tree.reload_file_lists(name)

    def on_new_frame_btn(self):
        rospy.loginfo("[MotionEditor] Creating new frame.")
        animation_name = self.motion_file_manager.get_animation_name()
        if not animation_name:
            QMessageBox.information(self, "Delete Frame", "No animation selected.")
            return
        self.animation_tree.create_new_frame(animation_name)
        self.animation_tree.reload_file_lists(animation_name)

    def on_delete_anim_btn(self):
        self.animation_tree.delete_animation()
        self.reload_animation_tree()

    def on_delete_frame_btn(self):
        rospy.loginfo("[MotionEditor] Deleting frame.")
        animation_name = self.motion_file_manager.get_animation_name()
        if not animation_name:
            QMessageBox.information(self, "Delete Frame", "No animation selected.")
            return
        self.animation_tree.delete_frame()
        self.animation_tree.reload_file_lists(animation_name)

    def on_tree_item_clicked(self, item):
        animation_item = item
        while animation_item.parent():
            animation_item = animation_item.parent()
        name = animation_item.text(0)
        rospy.loginfo(f"[MotionEditor] Tree item clicked: {name}")
        if name == self.motion_file_manager.get_animation_name():
            return
        self.load_animation_by_name(name)

    def on_tree_item_double_clicked(self, item):
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

    def load_animation_by_name(self, animation_name):
        if not self.confirm_save_if_unsaved_changes():
            return

        self.motion_file_manager.set_animation_name(animation_name)
        anim_data = self.motion_file_manager.get_animation_data()
        self.animation_flow_scene.set_animation_data(anim_data)
        self.animation_flow_scene.highlight_preview_path()

        try:
            frame_data = self.motion_file_manager.get_initial_frame()
            self.initial_joint_state = frame_data.get_joint_state()
            self.animation_visualizer.initial_joint_state = self.initial_joint_state
            self.animation_commander.initial_joint_state = self.initial_joint_state
        except Exception as e:
            rospy.logwarn(f"[MotionEditor] Failed to load initial_frame: {e}")
