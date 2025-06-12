import threading
from typing import Union

import rospy
from moveit_msgs.msg import DisplayRobotState
from moveit_msgs.msg import DisplayTrajectory
from moveit_msgs.msg import RobotState
from moveit_msgs.msg import RobotTrajectory
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint


class TrajectoryVisualizer:
    def __init__(self, use_state_mode: bool, playback_rate: float = 30.0):
        self.use_state_mode = use_state_mode
        self.playback_rate = playback_rate

        self._enabled = True
        self._current_joint_state = None

        self._playback_lock = threading.Lock()
        self._cancel_event = threading.Event()

        if self.use_state_mode:
            self._loop_enabled = True
            self.state_pub = rospy.Publisher("/display_planned_state", DisplayRobotState, queue_size=1)
            self._playback_thread = threading.Thread(target=self._state_mode_thread, daemon=True)
            self._playback_thread.start()
            rospy.loginfo("[TrajectoryVisualizer] Initialized in STATE mode.")
        else:
            self.path_pub = rospy.Publisher("/move_group/display_planned_path", DisplayTrajectory, queue_size=1)
            rospy.loginfo("[TrajectoryVisualizer] Initialized in PATH mode.")

        self.goal_state_pub = rospy.Publisher("/display_robot_state", DisplayRobotState, queue_size=1)
        self._trajectory = None

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    def is_enabled(self) -> bool:
        return self._enabled

    def enable_loop(self, enable: bool):
        if self.use_state_mode:
            self._loop_enabled = enable
            if enable:
                self._cancel_event.set()
        else:
            rospy.logwarn("Looping is only supported in state mode.")

    def set_current_joint_state(self, joint_state: JointState):
        if joint_state.name and joint_state.position:
            self._current_joint_state = JointState(name=joint_state.name[:], position=joint_state.position[:])

    def get_current_joint_state(self) -> JointState:
        return self._current_joint_state

    def visualize_goal_state(self, joint_state: JointState):
        if not self._enabled or not joint_state.name or not joint_state.position:
            return
        state_msg = RobotState(joint_state=joint_state)
        self.goal_state_pub.publish(DisplayRobotState(state=state_msg))

    def send_joint_state(self, joint_state: JointState, duration: float = 1.0):
        if not self._enabled or not joint_state.name or not joint_state.position:
            return

        if not self._current_joint_state:
            # First time: treat goal as both current and goal state
            self._current_joint_state = JointState(name=joint_state.name[:], position=joint_state.position[:])
            self.visualize_goal_state(joint_state)
            traj = JointTrajectory(joint_names=joint_state.name)
            point = JointTrajectoryPoint(
                time_from_start=rospy.Duration(duration),
                positions=joint_state.position,
                velocities=[0.0] * len(joint_state.position)
            )
            traj.points = [point]
            self.send_trajectory(traj)
        else:
            self.send_movement(self._current_joint_state, joint_state, duration)
            self.visualize_goal_state(joint_state)

    def send_movement(self, start: JointState, end: JointState, duration: float = 1.0):
        if not self._enabled or not start.name or not start.position or not end.name or not end.position:
            return

        aligned_start = JointState(name=end.name, position=self._align_positions(start, end))
        traj = JointTrajectory(joint_names=end.name)

        point0 = JointTrajectoryPoint(
            time_from_start=rospy.Duration(0.0),
            positions=aligned_start.position,
            velocities=[
                (b - a) / duration if duration > 0 else 0.0 for a,
                b in zip(
                    aligned_start.position,
                    end.position)])
        point1 = JointTrajectoryPoint(
            time_from_start=rospy.Duration(duration),
            positions=end.position,
            velocities=[0.0] * len(end.position)
        )

        traj.points = [point0, point1]
        self.send_trajectory(traj)

        # Update current joint state to the goal after sending trajectory
        self._current_joint_state = JointState(name=end.name[:], position=end.position[:])

    def send_trajectory(self, trajectory: JointTrajectory):
        if not self._enabled:
            return

        interpolated_traj = self._interpolate(trajectory, self.playback_rate)

        with self._playback_lock:
            self._trajectory = interpolated_traj

        # Update current_joint_state using the final trajectory point
        if interpolated_traj.points:
            self._current_joint_state = JointState(
                name=interpolated_traj.joint_names[:],
                position=interpolated_traj.points[-1].positions[:]
            )

        if self.use_state_mode:
            self._cancel_event.set()
        else:
            msg = DisplayTrajectory()
            msg.trajectory.append(RobotTrajectory(joint_trajectory=interpolated_traj))
            self.path_pub.publish(msg)

    def _align_positions(self, source: JointState, reference: Union[JointState, list]) -> list:
        ref_names = reference.name if isinstance(reference, JointState) else reference
        pos_dict = dict(zip(source.name, source.position))
        return [pos_dict.get(name, 0.0) for name in ref_names]

    def _interpolate(self, trajectory: JointTrajectory, rate: float) -> JointTrajectory:
        if len(trajectory.points) < 2:
            return trajectory

        result = JointTrajectory(joint_names=trajectory.joint_names)
        for i in range(len(trajectory.points) - 1):
            p0 = trajectory.points[i]
            p1 = trajectory.points[i + 1]
            t0, t1 = p0.time_from_start.to_sec(), p1.time_from_start.to_sec()
            dt = t1 - t0
            steps = max(int(dt * rate), 1)

            for step in range(steps):
                t = step / steps
                time_sec = t0 + t * dt
                interpolated_pos = [a + v * (time_sec - t0) for a, v in zip(p0.positions, p0.velocities)]
                bounded_pos = [
                    min(max(p1_i, p0_i), pi) if p0_i < p1_i else max(min(p1_i, p0_i), pi)
                    for pi, p0_i, p1_i in zip(interpolated_pos, p0.positions, p1.positions)
                ]
                pt = JointTrajectoryPoint(
                    time_from_start=rospy.Duration.from_sec(time_sec),
                    positions=bounded_pos,
                    velocities=p0.velocities
                )
                result.points.append(pt)

        result.points.append(trajectory.points[-1])
        return result

    def _state_mode_thread(self):
        while not rospy.is_shutdown():
            self._cancel_event.wait()
            self._cancel_event.clear()

            while not rospy.is_shutdown():
                with self._playback_lock:
                    traj = self._trajectory

                if not self._enabled:
                    rospy.sleep(1.0 / self.playback_rate)
                    continue

                if traj and traj.points:
                    for pt in traj.points:
                        if self._cancel_event.is_set():
                            break
                        state = RobotState(joint_state=JointState(
                            name=traj.joint_names,
                            position=pt.positions,
                            velocity=pt.velocities
                        ))
                        self.state_pub.publish(DisplayRobotState(state=state))
                        rospy.sleep(1.0 / self.playback_rate)
                    if not self._loop_enabled:
                        break
                else:
                    break

                if not self._loop_enabled or self._cancel_event.is_set():
                    break
