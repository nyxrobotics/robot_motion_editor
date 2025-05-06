import threading

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

    def set_in_frame(self, joint_state: JointState, move_duration: float = 1.0, wait_duration: float = 0.0):
        with self._lock:
            self.in_frame = (joint_state, move_duration, wait_duration)

    def set_current_frame(self, joint_state: JointState, move_duration: float = 1.0, wait_duration: float = 0.0):
        with self._lock:
            self.current_frame = (joint_state, move_duration, wait_duration)

    def set_out_frame(self, joint_state: JointState, move_duration: float = 1.0, wait_duration: float = 0.0):
        with self._lock:
            self.out_frame = (joint_state, move_duration, wait_duration)

    def get_in_trajectory(self) -> JointTrajectory:
        with self._lock:
            return self._make_trajectory_pair(self.in_frame, self.current_frame)

    def get_out_trajectory(self) -> JointTrajectory:
        with self._lock:
            return self._make_trajectory_pair(self.current_frame, self.out_frame)

    def play_in_trajectory(self):
        traj = self.get_in_trajectory()
        self.trajectory_visualizer.visualize_joint_trajectory(traj)

    def play_out_trajectory(self):
        traj = self.get_out_trajectory()
        self.trajectory_visualizer.visualize_joint_trajectory(traj)

    def play_in_out_trajectory(self):
        traj = self._make_trajectory_sequence([self.in_frame, self.current_frame, self.out_frame])
        self.trajectory_visualizer.visualize_joint_trajectory(traj)

    def _make_trajectory_pair(self, start_data, end_data) -> JointTrajectory:
        if start_data is None or end_data is None:
            return JointTrajectory()

        start_state, _, _ = start_data
        end_state, move_duration, wait_duration = end_data

        traj = JointTrajectory()
        traj.joint_names = end_state.name

        start_point = JointTrajectoryPoint()
        start_point.time_from_start = rospy.Duration(wait_duration)
        start_point.positions = self._get_aligned_joint_positions(start_state, end_state)
        start_point.velocities = [
            (b - a) / move_duration
            for a, b in zip(start_point.positions, end_state.position)
        ]

        end_point = JointTrajectoryPoint()
        end_point.time_from_start = rospy.Duration(wait_duration + move_duration)
        end_point.positions = end_state.position
        end_point.velocities = [0.0] * len(end_state.position)

        traj.points = [start_point, end_point]
        return traj

    def _make_trajectory_sequence(self, frame_data_list) -> JointTrajectory:
        traj = JointTrajectory()
        current_time = 0.0

        for i in range(len(frame_data_list) - 1):
            start_data = frame_data_list[i]
            end_data = frame_data_list[i + 1]

            if start_data is None or end_data is None:
                continue

            start_state, _, _ = start_data
            end_state, move_duration, wait_duration = end_data

            if not traj.joint_names:
                traj.joint_names = end_state.name

            aligned_start = self._get_aligned_joint_positions(start_state, end_state)

            point_start = JointTrajectoryPoint()
            point_start.time_from_start = rospy.Duration(current_time + wait_duration)
            point_start.positions = aligned_start
            point_start.velocities = [
                (b - a) / move_duration
                for a, b in zip(aligned_start, end_state.position)
            ]

            point_end = JointTrajectoryPoint()
            point_end.time_from_start = rospy.Duration(current_time + wait_duration + move_duration)
            point_end.positions = end_state.position
            point_end.velocities = [0.0] * len(end_state.position)

            traj.points.append(point_start)
            traj.points.append(point_end)

            current_time = point_end.time_from_start.to_sec()

        return traj

    def _get_aligned_joint_positions(self, current: JointState, target: JointState):
        return [
            current.position[current.name.index(name)] if name in current.name else 0.0
            for name in target.name
        ]
