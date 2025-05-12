import threading
from typing import List

import rospy
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint

from .trajectory_visualizer import TrajectoryVisualizer


class FrameVisualizer:
    def __init__(self, trajectory_visualizer: TrajectoryVisualizer):
        self.trajectory_visualizer = trajectory_visualizer
        self._lock = threading.Lock()
        self.in_frame = None
        self.current_frame = None
        self.out_frame = None
        self.initial_frame = None

    def set_initial_frame(self, joint_state: JointState, move_duration: float = 1.0, wait_duration: float = 0.0):
        with self._lock:
            self.initial_frame = (joint_state, move_duration, wait_duration)

    def set_in_frame(self, joint_state: JointState, move_duration: float = 1.0, wait_duration: float = 0.0):
        with self._lock:
            self.in_frame = (joint_state, move_duration, wait_duration)

    def set_current_frame(self, joint_state: JointState, move_duration: float = 1.0, wait_duration: float = 0.0):
        with self._lock:
            self.current_frame = (joint_state, move_duration, wait_duration)

    def set_out_frame(self, joint_state: JointState, move_duration: float = 1.0, wait_duration: float = 0.0):
        with self._lock:
            self.out_frame = (joint_state, move_duration, wait_duration)

    def reset_in_frame(self):
        with self._lock:
            self.in_frame = None

    def reset_current_frame(self):
        with self._lock:
            self.current_frame = None

    def reset_out_frame(self):
        with self._lock:
            self.out_frame = None

    def play_in_trajectory(self):
        traj = self._make_trajectory_sequence([self.in_frame, self.current_frame])
        self.trajectory_visualizer.visualize_joint_trajectory(traj)

    def play_out_trajectory(self):
        traj = self._make_trajectory_sequence([self.current_frame, self.out_frame])
        self.trajectory_visualizer.visualize_joint_trajectory(traj)

    def play_in_out_trajectory(self):
        traj = self._make_trajectory_sequence([self.in_frame, self.current_frame, self.out_frame])
        self.trajectory_visualizer.visualize_joint_trajectory(traj)

    def _make_trajectory_sequence(self, frame_data_list) -> JointTrajectory:
        traj = JointTrajectory()
        current_time = 0.0

        # Determine reference joint order from current_frame or first valid frame
        reference_names = None
        if self.current_frame is not None:
            reference_names = self.current_frame[0].name
        else:
            for data in frame_data_list:
                if data is not None:
                    reference_names = data[0].name
                    break
        if reference_names is None and self.initial_frame is not None:
            reference_names = self.initial_frame[0].name
        if reference_names is None:
            return traj

        traj.joint_names = reference_names

        for i in range(len(frame_data_list) - 1):
            start_data = frame_data_list[i]
            end_data = frame_data_list[i + 1]

            if start_data is None:
                start_data = self.initial_frame
            if end_data is None:
                end_data = self.initial_frame
            if start_data is None or end_data is None:
                continue

            start_state, _, _ = start_data
            end_state, move_duration, wait_duration = end_data

            aligned_start = self.trajectory_visualizer._get_aligned_joint_positions(start_state, reference_names)
            aligned_end = self.trajectory_visualizer._get_aligned_joint_positions(end_state, reference_names)

            point_start = JointTrajectoryPoint()
            point_start.time_from_start = rospy.Duration(current_time + wait_duration)
            point_start.positions = aligned_start
            point_start.velocities = [
                (b - a) / move_duration
                for a, b in zip(aligned_start, aligned_end)
            ]

            point_end = JointTrajectoryPoint()
            point_end.time_from_start = rospy.Duration(current_time + wait_duration + move_duration)
            point_end.positions = aligned_end
            point_end.velocities = [0.0] * len(aligned_end)

            traj.points.append(point_start)
            traj.points.append(point_end)

            current_time = point_end.time_from_start.to_sec()

        return traj
