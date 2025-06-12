import threading
from typing import Union

import rospy
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64
from trajectory_msgs.msg import JointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint


class TrajectoryCommander:
    def __init__(self, robot_name: str, joint_names: list, mode: str = 'position', playback_rate: float = 30.0):
        self.robot_name = robot_name
        self.joint_names = joint_names
        self.mode = mode.lower()
        self.playback_rate = playback_rate

        self._enabled = False
        self._torque_on = False
        self._last_goal_state = None

        self._playback_thread = None
        self._playback_lock = threading.Lock()
        self._cancel_event = threading.Event()

        self.position_publishers = {}
        self.trajectory_publisher = None

        if self.mode == 'position':
            for name in self.joint_names:
                topic = f"/{self.robot_name}/{name}_position/command"
                self.position_publishers[name] = rospy.Publisher(topic, Float64, queue_size=10)
            rospy.loginfo("[TrajectoryCommander] Initialized in POSITION mode.")
        elif self.mode == 'trajectory':
            topic = f"/{self.robot_name}/trajectory_controller/command"
            self.trajectory_publisher = rospy.Publisher(topic, JointTrajectory, queue_size=10)
            rospy.loginfo("[TrajectoryCommander] Initialized in TRAJECTORY mode.")
        else:
            raise ValueError(f"Invalid mode '{mode}'. Use 'trajectory' or 'position'.")

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    def is_enabled(self) -> bool:
        return self._enabled

    def torque_on(self):
        self._torque_on = True
        rospy.loginfo("[TrajectoryCommander] Torque ON")

    def torque_off(self):
        self._torque_on = False
        rospy.loginfo("[TrajectoryCommander] Torque OFF")

    def is_torque_on(self) -> bool:
        return self._torque_on

    def send_joint_state(self, joint_state: JointState, duration: float = 1.0):
        if not self._enabled or not self._torque_on:
            return
        if not joint_state.name or not joint_state.position:
            return
        if not self._last_goal_state:
            self._last_goal_state = JointState(name=joint_state.name[:], position=joint_state.position[:])
            traj = JointTrajectory(joint_names=joint_state.name)
            point = JointTrajectoryPoint(
                time_from_start=rospy.Duration(duration),
                positions=joint_state.position,
                velocities=[0.0] * len(joint_state.position)
            )
            traj.points = [point]
            self.send_trajectory(traj)
            return

        aligned_start = JointState(
            name=joint_state.name,
            position=self._align_positions(self._last_goal_state, joint_state)
        )
        traj = JointTrajectory(joint_names=joint_state.name)
        point0 = JointTrajectoryPoint(
            time_from_start=rospy.Duration(0.0),
            positions=aligned_start.position,
            velocities=[
                (b - a) / duration if duration > 0 else 0.0 for a, b in zip(
                    aligned_start.position, joint_state.position)])
        point1 = JointTrajectoryPoint(
            time_from_start=rospy.Duration(duration),
            positions=joint_state.position,
            velocities=[0.0] * len(joint_state.position)
        )
        traj.points = [point0, point1]
        self.send_trajectory(traj)
        self._last_goal_state = JointState(name=joint_state.name[:], position=joint_state.position[:])

    def send_movement(self, start: JointState, end: JointState, duration: float = 1.0):
        if not self._enabled or not self._torque_on:
            return
        if not start.name or not start.position or not end.name or not end.position:
            return

        aligned_start = JointState(name=end.name, position=self._align_positions(start, end))
        self._last_goal_state = aligned_start

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

    def send_trajectory(self, trajectory: JointTrajectory):
        if not self._enabled or not self._torque_on:
            return
        if not trajectory.joint_names or not trajectory.points:
            return

        interpolated_traj = self._interpolate(trajectory, self.playback_rate)
        if self.mode == 'trajectory':
            self.trajectory_publisher.publish(interpolated_traj)
            self._last_goal_state = JointState(
                name=trajectory.joint_names[:], position=trajectory.points[-1].positions[:])
        else:
            self._start_position_playback(interpolated_traj)

    def set_last_goal_state(self, joint_state: JointState):
        if not joint_state.name or not joint_state.position:
            return
        self._last_goal_state = JointState(name=joint_state.name[:], position=joint_state.position[:])

    def get_last_goal_state(self) -> JointState:
        return self._last_goal_state

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

    def _start_position_playback(self, trajectory: JointTrajectory):
        with self._playback_lock:
            if self._playback_thread and self._playback_thread.is_alive():
                self._cancel_event.set()
                self._playback_thread.join()

            self._cancel_event.clear()
            self._playback_thread = threading.Thread(
                target=self._playback_trajectory_thread, args=(trajectory,)
            )
            self._playback_thread.start()

    def _playback_trajectory_thread(self, trajectory: JointTrajectory):
        if len(trajectory.points) < 2 or rospy.is_shutdown():
            return

        rate = rospy.Rate(self.playback_rate)
        joint_names = trajectory.joint_names

        for i in range(len(trajectory.points) - 1):
            if rospy.is_shutdown():
                return
            p0 = trajectory.points[i]
            p1 = trajectory.points[i + 1]

            t0 = p0.time_from_start.to_sec()
            t1 = p1.time_from_start.to_sec()
            dt = t1 - t0
            steps = max(1, int(dt * self.playback_rate))

            for step in range(steps):
                if self._cancel_event.is_set() or not self._torque_on:
                    return

                t = (step + 1) / steps
                interpolated_pos = [a + t * (b - a) for a, b in zip(p0.positions, p1.positions)]

                for name, pos in zip(joint_names, interpolated_pos):
                    if name in self.position_publishers:
                        self.position_publishers[name].publish(Float64(pos))

                self._last_goal_state = JointState(name=joint_names[:], position=interpolated_pos[:])
                rate.sleep()
