import rospy
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog

from ..logic.frame_file_manager import FrameData
from ..logic.joint_data_manager import JointDataManager
from ..logic.motion_directory_manager import MotionDirectoryManager
from ..robot_interface.trajectory_commander import TrajectoryCommander
from ..visualizer.trajectory_visualizer import TrajectoryVisualizer
from .animation_editor_items import FrameBlockItem
from .animation_editor_items import IfBlockItem
from .animation_editor_items import StartBlockItem
from .animation_editor_items import SwitchBlockItem
from .frame_editor import FrameEditorDialog
from .if_condition_editor import IfConditionEditorDialog
from .initial_frame_editor import InitialFrameEditorDialog
from .switch_condition_editor import SwitchConditionEditorDialog


class AnimationItemEditorLauncher:
    def __init__(
            self,
            joint_data_manager: JointDataManager,
            motion_directory_manager: MotionDirectoryManager,
            trajectory_visualizer: TrajectoryVisualizer,
            trajectory_commander: TrajectoryCommander):
        self.joint_data_manager = joint_data_manager
        self.motion_directory_manager = motion_directory_manager
        self.item_file_manager = animtion_item_data
        self.trajectory_visualizer = trajectory_visualizer
        self.trajectory_commander = trajectory_commander
        self.open_editors = {}  # key: f"type:filename" or "initial_frame"

    def open_editor_by_block(self, block,
                             prev_frame_data: FrameData = None,
                             next_frame_data: FrameData = None):
        if isinstance(block, FrameBlockItem):
            self._open_frame_editor(block, prev_frame_data, next_frame_data)
        elif isinstance(block, IfBlockItem):
            self._open_if_editor(block)
        elif isinstance(block, SwitchBlockItem):
            self._open_switch_editor(block)
        elif isinstance(block, StartBlockItem):
            self._open_initial_frame_editor()
        else:
            rospy.logwarn(f"[EditorLauncher] Unknown block type: {type(block)}")

    def open_editor_by_type(self, type: str, name: str = ""):
        if type == "frame":
            fake_block = FrameBlockItem(id=0, filename=name)
            self._open_frame_editor(fake_block, prev_frame_data=None, next_frame_data=None)
        elif type == "if":
            fake_block = IfBlockItem(id=0, filename=name)
            self._open_if_editor(fake_block)
        elif type == "switch":
            fake_block = SwitchBlockItem(id=0, filename=name)
            self._open_switch_editor(fake_block)
        elif type == "initial_frame":
            self._open_initial_frame_editor()
        else:
            rospy.logwarn(f"[EditorLauncher] Unknown type for open_editor_by_type: {type}")

    def _open_frame_editor(self, block, prev_frame_data, next_frame_data):
        key = f"frame:{block.filename}"
        if key in self.open_editors:
            dlg = self.open_editors[key]
            if dlg.isVisible():
                dlg.raise_()
                dlg.activateWindow()
                # Update prev/next frame if they differ
                if prev_frame_data:
                    dlg.set_prev_frame_data(prev_frame_data)
                if next_frame_data:
                    dlg.set_next_frame_data(next_frame_data)
                return

        dlg = FrameEditorDialog(
            joint_data_manager=self.joint_data_manager,
            motion_directory_manager=self.motion_directory_manager,
            filename=block.filename,
            frame_block=block,
            trajectory_visualizer=self.trajectory_visualizer,
            trajectory_commander=self.trajectory_commander
        )
        if prev_frame_data:
            dlg.set_prev_frame_data(prev_frame_data)
        if next_frame_data:
            dlg.set_next_frame_data(next_frame_data)
        self._register_editor(key, dlg)

    def _open_initial_frame_editor(self):
        key = "initial_frame"
        if self._already_open(key):
            return
        dlg = InitialFrameEditorDialog(
            joint_data_manager=self.joint_data_manager,
            motion_directory_manager=self.motion_directory_manager,
            trajectory_visualizer=self.trajectory_visualizer,
            trajectory_commander=self.trajectory_commander
        )
        self._register_editor(key, dlg)

    def _open_if_editor(self, block):
        key = f"if:{block.filename}"
        if self._already_open(key):
            return
        dlg = IfConditionEditorDialog(
            joint_data_manager=self.joint_data_manager,
            motion_directory_manager=self.motion_directory_manager,
            filename=block.filename
        )
        self._register_editor(key, dlg)

    def _open_switch_editor(self, block):
        key = f"switch:{block.filename}"
        if self._already_open(key):
            return
        dlg = SwitchConditionEditorDialog(
            joint_data_manager=self.joint_data_manager,
            motion_directory_manager=self.motion_directory_manager,
            filename=block.filename
        )
        if hasattr(block.scene(), "update_switch_block"):
            dlg.finished.connect(lambda result_code: (
                block.scene().update_switch_block(block.filename, dlg.result.get("num_cases", 2))
                if result_code == QDialog.Accepted and dlg.result else None
            ))
        self._register_editor(key, dlg)

    def _already_open(self, key):
        if key in self.open_editors and self.open_editors[key].isVisible():
            self.open_editors[key].raise_()
            self.open_editors[key].activateWindow()
            return True
        return False

    def _register_editor(self, key, dlg):
        dlg.setAttribute(Qt.WA_DeleteOnClose)
        dlg.show()
        self.open_editors[key] = dlg
        dlg.destroyed.connect(lambda: self.open_editors.pop(key, None))
