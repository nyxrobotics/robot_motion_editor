import rospy
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint


class FrameCommander:
    def __init__(self, trajectory_commander):
        self.trajectory_commander = trajectory_commander
        self.initial_frame = None
        self.in_frame = None
        self.current_frame = None
        self.out_frame = None

    def set_frame(self, name, joint_state: JointState, move_duration: float = 1.0, wait_duration: float = 0.0):
        setattr(self, name, (joint_state, move_duration, wait_duration))

    def reset_frame(self, name):
        setattr(self, name, None)

    def set_initial_frame(self, joint_state: JointState, move_duration: float = 1.0, wait_duration: float = 0.0):
        self.set_frame("initial_frame", joint_state, move_duration, wait_duration)

    def set_previous_frame(self, joint_state: JointState, move_duration: float = 1.0, wait_duration: float = 0.0):
        self.set_frame("in_frame", joint_state, move_duration, wait_duration)

    def set_current_frame(self, joint_state: JointState, move_duration: float = 1.0, wait_duration: float = 0.0):
        self.set_frame("current_frame", joint_state, move_duration, wait_duration)

    def set_next_frame(self, joint_state: JointState, move_duration: float = 1.0, wait_duration: float = 0.0):
        self.set_frame("out_frame", joint_state, move_duration, wait_duration)

    def send_frame_sequence(self, sequence_names):
        frames = [getattr(self, name, None) for name in sequence_names]
        traj = self._build_trajectory(frames)
        if traj:
            self.trajectory_commander.send_trajectory(traj)

    def _build_trajectory(self, frame_data_list):
        traj = JointTrajectory()
        current_time = 0.0

        reference_names = None
        for data in frame_data_list:
            if data is not None:
                reference_names = data[0].name
                break

        if reference_names is None and self.initial_frame is not None:
            reference_names = self.initial_frame[0].name
        if reference_names is None:
            rospy.logwarn("[FrameCommander] Cannot build trajectory: no valid frame data.")
            return None

        traj.joint_names = reference_names

        for i in range(len(frame_data_list) - 1):
            start_data = frame_data_list[i] or self.initial_frame
            end_data = frame_data_list[i + 1] or self.initial_frame
            if start_data is None or end_data is None:
                continue

            start_state, _, _ = start_data
            end_state, move_duration, wait_duration = end_data

            aligned_start = self._align_positions(start_state, reference_names)
            aligned_end = self._align_positions(end_state, reference_names)

            point_start = JointTrajectoryPoint()
            point_start.time_from_start = rospy.Duration(current_time)
            point_start.positions = aligned_start
            point_start.velocities = [
                (b - a) / move_duration if move_duration > 0 else 0.0
                for a, b in zip(aligned_start, aligned_end)
            ]

            point_end = JointTrajectoryPoint()
            point_end.time_from_start = rospy.Duration(current_time + move_duration)
            point_end.positions = aligned_end
            point_end.velocities = [0.0] * len(reference_names)

            traj.points.append(point_start)
            traj.points.append(point_end)

            current_time += move_duration + wait_duration

        return traj

    def _align_positions(self, joint_state: JointState, reference_names):
        source_dict = dict(zip(joint_state.name, joint_state.position))
        return [source_dict.get(name, 0.0) for name in reference_names]
