import threading
from typing import List

import rospy
from moveit_msgs.msg import DisplayRobotState
from moveit_msgs.msg import DisplayTrajectory
from moveit_msgs.msg import RobotState
from moveit_msgs.msg import RobotTrajectory
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint


class TrajectoryVisualizer:
    def __init__(self, visualize_as_state: bool, rate: float = 30.0):
        self.visualize_as_state = visualize_as_state
        self.rate = rate

        self._lock = threading.Lock()
        self._trajectory = None

        if self.visualize_as_state:
            self.pub = rospy.Publisher("/display_planned_state", DisplayRobotState, queue_size=1)
            self.cancel_event = threading.Event()
            self.loop_enabled = True
            self._playback_thread = threading.Thread(target=self._playback_loop)
            self._playback_thread.daemon = True
            self._playback_thread.start()
        else:
            self.pub = rospy.Publisher("/move_group/display_planned_path", DisplayTrajectory, queue_size=1)

        self.goal_state_pub = rospy.Publisher("/display_robot_state", DisplayRobotState, queue_size=1)

    def visualize_current2target(self, current: JointState, target: JointState, duration: float = 1.0):
        start_state = JointState(
            name=target.name,
            position=self._get_aligned_joint_positions(current, target)
        )

        traj = JointTrajectory()
        traj.joint_names = target.name

        point_start = JointTrajectoryPoint()
        point_start.time_from_start = rospy.Duration(0.0)
        point_start.positions = start_state.position
        point_start.velocities = [
            1000.0 if duration == 0.0 else (b - a) / duration for a, b in zip(start_state.position, target.position)
        ]

        point_end = JointTrajectoryPoint()
        point_end.time_from_start = rospy.Duration(duration)
        point_end.positions = target.position
        point_end.velocities = [0.0] * len(target.position)

        traj.points = [point_start, point_end]
        self.visualize_joint_trajectory(traj)

    def visualize_joint_trajectory(self, trajectory: JointTrajectory):
        interpolated = self._interpolate_joint_trajectory(trajectory, self.rate)

        with self._lock:
            self._trajectory = interpolated

        if self.visualize_as_state:
            self.cancel_event.set()
        else:
            traj_msg = DisplayTrajectory()
            traj_msg.trajectory.append(RobotTrajectory(joint_trajectory=interpolated))
            self.pub.publish(traj_msg)

    def publish_goal_state(self, joint_state: JointState):
        robot_state = RobotState()
        robot_state.joint_state = joint_state
        self.goal_state_pub.publish(DisplayRobotState(state=robot_state))

    def enable_loop(self, enabled: bool):
        if self.visualize_as_state:
            self.loop_enabled = enabled
            if enabled:
                self.cancel_event.set()
        else:
            rospy.logwarn("Looping is only supported in state visualization mode.")

    def _publish_trajectory_once(self, current, target, duration):
        if current is None or target is None:
            return

        start_state = JointState(
            name=target.name,
            position=self._get_aligned_joint_positions(current, target)
        )

        traj = JointTrajectory()
        traj.joint_names = target.name

        point_start = JointTrajectoryPoint()
        point_start.time_from_start = rospy.Duration(0.0)
        point_start.positions = start_state.position
        point_start.velocities = [
            1000.0 if duration == 0.0 else (b - a) / duration for a, b in zip(start_state.position, target.position)
        ]

        point_end = JointTrajectoryPoint()
        point_end.time_from_start = rospy.Duration(duration)
        point_end.positions = target.position
        point_end.velocities = [0.0] * len(target.position)

        traj.points = [point_start, point_end]

        traj_msg = DisplayTrajectory()
        traj_msg.trajectory_start.joint_state = start_state
        traj_msg.trajectory.append(RobotTrajectory(joint_trajectory=traj))
        self.pub.publish(traj_msg)

    def _playback_loop(self):
        while not rospy.is_shutdown():
            self.cancel_event.wait()
            self.cancel_event.clear()

            while not rospy.is_shutdown():
                with self._lock:
                    trajectory = self._trajectory

                if trajectory and trajectory.points:
                    for point in trajectory.points:
                        if self.cancel_event.is_set():
                            break
                        robot_state = RobotState()
                        robot_state.joint_state.name = trajectory.joint_names
                        robot_state.joint_state.position = point.positions
                        robot_state.joint_state.velocity = point.velocities
                        self.pub.publish(DisplayRobotState(state=robot_state))
                        rospy.sleep(1.0 / self.rate)
                    if not self.loop_enabled:
                        break
                else:
                    break

                if not self.loop_enabled or self.cancel_event.is_set():
                    break

    def _interpolate_joint_trajectory(self, trajectory: JointTrajectory, rate: float) -> JointTrajectory:
        if len(trajectory.points) < 2:
            return trajectory

        result = JointTrajectory()
        result.joint_names = trajectory.joint_names

        for i in range(len(trajectory.points) - 1):
            p0 = trajectory.points[i]
            p1 = trajectory.points[i + 1]
            t0 = p0.time_from_start.to_sec()
            t1 = p1.time_from_start.to_sec()
            dt = t1 - t0
            steps = max(int(dt * rate), 1)

            for step in range(steps):
                t = step / steps
                time = t0 + t * dt
                pos = [a + v * (time - t0) for a, v in zip(p0.positions, p0.velocities)]

                pos = [
                    min(max(p1_i, p0_i), p_i) if p0_i < p1_i else max(min(p1_i, p0_i), p_i)
                    for p_i, p0_i, p1_i in zip(pos, p0.positions, p1.positions)
                ]

                point = JointTrajectoryPoint()
                point.time_from_start = rospy.Duration.from_sec(time)
                point.positions = pos
                point.velocities = p0.velocities
                result.points.append(point)

        result.points.append(trajectory.points[-1])
        return result

    def _get_aligned_joint_positions(self, source: JointState, reference_names):
        if isinstance(reference_names, JointState):
            reference_names = reference_names.name

        source_dict = dict(zip(source.name, source.position))
        aligned_positions = [source_dict.get(name, 0.0) for name in reference_names]
        return aligned_positions
