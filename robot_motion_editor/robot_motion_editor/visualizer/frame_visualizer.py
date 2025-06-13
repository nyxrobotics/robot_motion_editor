import threading

import rospy
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint

from ..logic.frame_file_manager import FrameData
from .trajectory_visualizer import TrajectoryVisualizer


class FrameVisualizer:
    def __init__(self, trajectory_visualizer: TrajectoryVisualizer):
        self.trajectory_visualizer = trajectory_visualizer
        self._lock = threading.Lock()
        self.initial_frame = None
        self.previous_frame = None
        self.current_frame = None
        self.next_frame = None

    def set_frame(self, name: str, frame_data: FrameData):
        with self._lock:
            setattr(self, name, frame_data)

    def reset_frame(self, name: str):
        with self._lock:
            setattr(self, name, None)

    def set_initial_frame(self, frame_data: FrameData):
        self.set_frame("initial_frame", frame_data)

    def set_previous_frame(self, frame_data: FrameData):
        self.set_frame("previous_frame", frame_data)

    def set_current_frame(self, frame_data: FrameData):
        self.set_frame("current_frame", frame_data)

    def set_next_frame(self, frame_data: FrameData):
        self.set_frame("next_frame", frame_data)

    def play_previous_trajectory(self):
        self.send_frame_sequence(["previous_frame", "current_frame"])

    def play_full_trajectory(self):
        self.send_frame_sequence(["previous_frame", "current_frame", "next_frame"])

    def play_next_trajectory(self):
        self.send_frame_sequence(["current_frame", "next_frame"])

    def reset_initial_frame(self):
        self.reset_frame("initial_frame")

    def reset_previous_frame(self):
        self.reset_frame("previous_frame")

    def reset_current_frame(self):
        self.reset_frame("current_frame")

    def reset_next_frame(self):
        self.reset_frame("next_frame")

    def send_frame_sequence(self, sequence_names):
        frames = []
        for name in sequence_names:
            frame = getattr(self, name, None)
            if isinstance(frame, FrameData):
                frames.append(frame)
            elif frame is not None:
                rospy.logwarn(f"[FrameVisualizer] Frame '{name}' is not a FrameData instance.")
        traj = self._build_trajectory(frames)
        if traj and traj.points:
            self.trajectory_visualizer.send_trajectory(traj)

    def _build_trajectory(self, frame_data_list: list) -> JointTrajectory:
        traj = JointTrajectory()
        current_time = 0.0

        # Determine joint_names from the first valid frame
        reference_names = None
        for frame in frame_data_list:
            if isinstance(frame, FrameData):
                reference_names = frame.get_joint_names()
                break

        if reference_names is None and isinstance(self.initial_frame, FrameData):
            reference_names = self.initial_frame.get_joint_names()
        if reference_names is None:
            return traj  # No valid frame data found

        traj.joint_names = reference_names

        for i in range(len(frame_data_list) - 1):
            start_frame = frame_data_list[i] or self.initial_frame
            end_frame = frame_data_list[i + 1] or self.initial_frame

            if not isinstance(start_frame, FrameData) or not isinstance(end_frame, FrameData):
                continue

            # Ensure joint_names are consistent
            if start_frame.get_joint_names() != reference_names:
                start_frame.set_joint_names(reference_names)
            if end_frame.get_joint_names() != reference_names:
                end_frame.set_joint_names(reference_names)

            start_state = start_frame.get_joint_state()
            end_state = end_frame.get_joint_state()
            move_duration = end_frame.move_duration
            wait_duration = end_frame.wait_duration

            start_positions = start_state.position
            end_positions = end_state.position

            # Retrieve speed_scale for each joint
            speed_scale_dict = {
                name: end_frame.get_speed_scale(name) for name in reference_names
            }

            point_start = JointTrajectoryPoint()
            point_start.time_from_start = rospy.Duration(current_time)
            point_start.positions = start_positions
            point_start.velocities = []

            for j, (a, b) in enumerate(zip(start_positions, end_positions)):
                name = reference_names[j]
                scale = speed_scale_dict.get(name, 1.0)
                if scale <= 0.0:
                    scale = 1000.0
                velocity = ((b - a) / move_duration) * scale if move_duration > 0.0 else 0.0
                point_start.velocities.append(velocity)

            point_end = JointTrajectoryPoint()
            point_end.time_from_start = rospy.Duration(current_time + move_duration + wait_duration)
            point_end.positions = end_positions
            point_end.velocities = [0.0] * len(end_positions)

            traj.points.append(point_start)
            traj.points.append(point_end)

            current_time = point_end.time_from_start.to_sec()

        return traj
