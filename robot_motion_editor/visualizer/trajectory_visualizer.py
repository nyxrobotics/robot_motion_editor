import threading

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

        if self.visualize_as_state:
            self._lock = threading.Lock()
            self._current = None
            self._target = None
            self._duration = 1.0
            self.pub = rospy.Publisher("/display_planned_state", DisplayRobotState, queue_size=1)
            self.cancel_event = threading.Event()
            self.loop_enabled = True
            self._playback_thread = threading.Thread(target=self._playback_loop)
            self._playback_thread.daemon = True
            self._playback_thread.start()
        else:
            self.pub = rospy.Publisher("/move_group/display_planned_path", DisplayTrajectory, queue_size=1)

        self.goal_state_pub = rospy.Publisher("/display_robot_state", DisplayRobotState, queue_size=1)

    def visualize_current2target(self, current: JointState, target: JointState, duration: float = None):
        if self.visualize_as_state:
            with self._lock:
                self._current = current
                self._target = target
                self.duration = duration if duration is not None else self.duration
            self.cancel_event.set()
        else:
            self._publish_trajectory_once(current, target, duration)

    def publish_goal_state(self, joint_state: JointState):
        robot_state = RobotState()
        robot_state.joint_state = joint_state
        self.goal_state_pub.publish(DisplayRobotState(state=robot_state))

    def enable_loop(self, enabled: bool):
        if self.visualize_as_state:
            self.loop_enabled = enabled
            if enabled:
                self.cancel_event.set()
        elif enabled:
            rospy.logwarn("Looping is only supported in state visualization mode.")

    def _publish_trajectory_once(self, current, target, duration):
        if current is None:
            rospy.logwarn("Current joint state is None.")
            return
        if target is None:
            rospy.logwarn("Target joint state is None.")
            return

        start_state = JointState(
            name=target.name,
            position=self._get_aligned_joint_positions(current, target)
        )
        trajectory = self._interpolate_trajectory(start_state, target, duration, self.rate)

        traj_msg = DisplayTrajectory()
        traj_msg.trajectory_start.joint_state = start_state
        traj_msg.trajectory.append(RobotTrajectory(joint_trajectory=trajectory))
        self.pub.publish(traj_msg)

    def _playback_loop(self):
        while not rospy.is_shutdown():
            self.cancel_event.wait()
            self.cancel_event.clear()

            while not rospy.is_shutdown():
                with self._lock:
                    current = self._current
                    target = self._target
                    duration = self.duration

                if current is None or target is None:
                    break

                start_state = JointState(
                    name=target.name,
                    position=self._get_aligned_joint_positions(current, target)
                )
                trajectory = self._interpolate_trajectory(start_state, target, duration, self.rate)

                for point in trajectory.points:
                    if self.cancel_event.is_set():
                        break
                    robot_state = RobotState()
                    robot_state.joint_state.name = trajectory.joint_names
                    robot_state.joint_state.position = point.positions
                    self.pub.publish(DisplayRobotState(state=robot_state))
                    rospy.sleep(1.0 / self.rate)

                if not self.loop_enabled or self.cancel_event.is_set():
                    break

    def _interpolate_trajectory(self, current, target, duration, rate):
        traj = JointTrajectory()
        traj.joint_names = target.name
        steps = int(duration * rate)
        for step in range(steps + 1):
            t = step / steps
            point = JointTrajectoryPoint()
            point.time_from_start = rospy.Duration.from_sec(t * duration)
            point.positions = [
                (1 - t) * c + t * tgt for c, tgt in zip(current.position, target.position)
            ]
            point.velocities = [0.0] * len(point.positions)
            traj.points.append(point)
        return traj

    def _get_aligned_joint_positions(self, current, target):
        return [
            current.position[current.name.index(name)] if name in current.name else 0.0
            for name in target.name
        ]
