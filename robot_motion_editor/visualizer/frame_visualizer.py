import threading

import rospy
from moveit_msgs.msg import DisplayTrajectory
from moveit_msgs.msg import RobotTrajectory
from trajectory_msgs.msg import JointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint


class FrameVisualizer:
    def __init__(self, rate: float = 30.0):
        self.in_trajectory = None
        self.current_trajectory = None
        self.out_trajectory = None

        self.loop_enabled = False
        self._rate = rate
        self._lock = threading.Lock()
        self._trajectory = None
        self._playback_cancel_event = threading.Event()
        self._playback_thread = threading.Thread(target=self._playback_loop)
        self._playback_thread.daemon = True
        self._playback_thread.start()

        self.pub = rospy.Publisher("/move_group/display_planned_path", DisplayTrajectory, queue_size=1)

    def set_in_trajectory(self, traj: JointTrajectory):
        with self._lock:
            self.in_trajectory = traj
        self._request_replay()

    def set_current_trajectory(self, traj: JointTrajectory):
        with self._lock:
            self.current_trajectory = traj
        self._request_replay()

    def set_out_trajectory(self, traj: JointTrajectory):
        with self._lock:
            self.out_trajectory = traj
        self._request_replay()

    def enable_loop(self, enabled: bool):
        with self._lock:
            self.loop_enabled = enabled
        self._request_replay()

    def play_in_current(self):
        with self._lock:
            self._trajectory = self._concat_trajectories([self.in_trajectory, self.current_trajectory])
        self._request_replay()

    def play_current_out(self):
        with self._lock:
            self._trajectory = self._concat_trajectories([self.current_trajectory, self.out_trajectory])
        self._request_replay()

    def play_in_current_out(self):
        with self._lock:
            self._trajectory = self._concat_trajectories(
                [self.in_trajectory, self.current_trajectory, self.out_trajectory])
        self._request_replay()

    def _concat_trajectories(self, trajs):
        combined = JointTrajectory()
        current_time = 0.0
        for traj in trajs:
            if traj is None or not traj.points:
                continue
            if not combined.joint_names:
                combined.joint_names = traj.joint_names
            for pt in traj.points:
                new_pt = JointTrajectoryPoint()
                new_pt.positions = pt.positions
                new_pt.velocities = pt.velocities
                new_pt.time_from_start = rospy.Duration.from_sec(current_time + pt.time_from_start.to_sec())
                combined.points.append(new_pt)
            current_time = combined.points[-1].time_from_start.to_sec()
        return combined

    def _request_replay(self):
        self._playback_cancel_event.set()

    def _playback_loop(self):
        while not rospy.is_shutdown():
            self._playback_cancel_event.wait()
            self._playback_cancel_event.clear()

            while not rospy.is_shutdown():
                with self._lock:
                    traj = self._trajectory

                if traj and traj.points:
                    traj_msg = DisplayTrajectory()
                    traj_msg.trajectory.append(RobotTrajectory(joint_trajectory=traj))
                    self.pub.publish(traj_msg)

                    total_time = traj.points[-1].time_from_start.to_sec()
                    start_time = rospy.Time.now().to_sec()

                    while rospy.Time.now().to_sec() - start_time < total_time:
                        if self._playback_cancel_event.is_set():
                            break
                        rospy.sleep(0.01)

                    if self._playback_cancel_event.is_set():
                        break

                    if not self.loop_enabled:
                        break
                else:
                    break
