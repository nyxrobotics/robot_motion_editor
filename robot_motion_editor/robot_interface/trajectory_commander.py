import threading

import rospy
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64
from trajectory_msgs.msg import JointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint


class TrajectoryCommander:
    def __init__(self, robot_name: str, joint_names: list, mode: str = 'position', rate: float = 30.0):
        """
        Initialize the TrajectoryCommander.

        Args:
            robot_name: Robot namespace prefix (e.g., 'my_robot')
            joint_names: List of joint names (e.g., ['joint1', 'joint2'])
            mode: 'trajectory' for JointTrajectoryController or 'position' for JointPositionController
            rate: Playback rate in Hz when using position mode
        """
        self.robot_name = robot_name
        self.joint_names = joint_names
        self.mode = mode.lower()
        self.rate = rate
        self._last_goal_state = None
        self._enabled = True

        self._playback_thread = None
        self._playback_lock = threading.Lock()
        self._playback_cancel_event = threading.Event()

        self.position_publishers = {}
        self.trajectory_publisher = None

        if self.mode == 'position':
            for joint in joint_names:
                topic = f"/{self.robot_name}/{joint}_position/command"
                self.position_publishers[joint] = rospy.Publisher(topic, Float64, queue_size=10)
            rospy.loginfo("[TrajectoryCommander] Initialized in POSITION mode.")
        elif self.mode == 'trajectory':
            topic = f"/{self.robot_name}/trajectory_controller/command"
            self.trajectory_publisher = rospy.Publisher(topic, JointTrajectory, queue_size=10)
            rospy.loginfo("[TrajectoryCommander] Initialized in TRAJECTORY mode.")
        else:
            raise ValueError(f"Invalid mode '{mode}'. Use 'trajectory' or 'position'.")

    def enable(self):
        """Enable command publishing."""
        self._enabled = True

    def disable(self):
        """Disable command publishing."""
        self._enabled = False

    def is_enabled(self) -> bool:
        """Check if publishing is currently enabled."""
        return self._enabled

    def send_joint_state(self, joint_state: JointState, duration: float = 1.0):
        """
        Send a single JointState as target position.

        Args:
            joint_state: Target joint state
            duration: Motion duration (used only in trajectory mode)
        """
        if not self._enabled:
            # rospy.logwarn("[TrajectoryCommander] Command ignored: commander is disabled.")
            return

        if self.mode == 'trajectory':
            traj = JointTrajectory()
            traj.joint_names = joint_state.name
            point = JointTrajectoryPoint()
            point.positions = joint_state.position
            point.velocities = [0.0] * len(joint_state.position)
            point.time_from_start = rospy.Duration(duration)
            traj.points = [point]
            self.trajectory_publisher.publish(traj)
        else:
            for name, pos in zip(joint_state.name, joint_state.position):
                if name in self.position_publishers:
                    self.position_publishers[name].publish(Float64(pos))

        self._last_goal_state = JointState(name=joint_state.name[:], position=joint_state.position[:])

    def send_trajectory(self, trajectory: JointTrajectory):
        """
        Send a full trajectory.

        Args:
            trajectory: JointTrajectory message
        """
        if not self._enabled:
            # rospy.logwarn("[TrajectoryCommander] Trajectory ignored: commander is disabled.")
            return

        if self.mode == 'trajectory':
            self.trajectory_publisher.publish(trajectory)
            if trajectory.points:
                last = trajectory.points[-1]
                self._last_goal_state = JointState(name=trajectory.joint_names[:], position=last.positions[:])
        else:
            self._start_position_mode_playback(trajectory)

    def _start_position_mode_playback(self, trajectory: JointTrajectory):
        """
        Start threaded playback for position mode (interpolated Float64 publishing).
        """
        with self._playback_lock:
            if self._playback_thread and self._playback_thread.is_alive():
                self._playback_cancel_event.set()
                self._playback_thread.join()

            self._playback_cancel_event.clear()
            self._playback_thread = threading.Thread(
                target=self._playback_trajectory_in_position_mode, args=(trajectory,)
            )
            self._playback_thread.start()

    def _playback_trajectory_in_position_mode(self, trajectory: JointTrajectory):
        """
        Interpolate and publish Float64 commands per joint at fixed rate based on trajectory.
        """
        if len(trajectory.points) < 2:
            return

        joint_names = trajectory.joint_names
        rate = rospy.Rate(self.rate)

        for i in range(len(trajectory.points) - 1):
            p0 = trajectory.points[i]
            p1 = trajectory.points[i + 1]

            t0 = p0.time_from_start.to_sec()
            t1 = p1.time_from_start.to_sec()
            duration = t1 - t0
            steps = max(1, int(duration * self.rate))

            for s in range(steps):
                if self._playback_cancel_event.is_set():
                    return

                t = (s + 1) / steps
                interpolated_pos = [a + t * (b - a) for a, b in zip(p0.positions, p1.positions)]

                for name, pos in zip(joint_names, interpolated_pos):
                    if name in self.position_publishers:
                        self.position_publishers[name].publish(Float64(pos))

                rate.sleep()

        self._last_goal_state = JointState(
            name=joint_names[:], position=trajectory.points[-1].positions[:]
        )

    def get_last_goal_state(self) -> JointState:
        """
        Return the last sent goal state (JointState), or None if not sent yet.
        """
        return self._last_goal_state
