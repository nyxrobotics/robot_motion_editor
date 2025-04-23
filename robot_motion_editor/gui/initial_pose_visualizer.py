import copy
import math
import threading

import rospy
from moveit_msgs.msg import DisplayRobotState
from moveit_msgs.msg import DisplayTrajectory
from moveit_msgs.msg import RobotState
from moveit_msgs.msg import RobotTrajectory
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint


class InitialPoseVisualizer:
    def __init__(self, joint_names):
        self.joint_names = joint_names
        self.lock = threading.Lock()
        self.current_joint_state = None
        self.last_target = None

        self.traj_pub = rospy.Publisher("/move_group/display_planned_path", DisplayTrajectory, queue_size=1)
        self.joint_state_sub = rospy.Subscriber("/joint_states", JointState, self.joint_state_callback)
        self.goal_pub = rospy.Publisher("/move_group/display_robot_state", DisplayRobotState, queue_size=1)

    def joint_state_callback(self, msg):
        with self.lock:
            self.current_joint_state = msg

    def update_target_pose(self, joint_state_msg):
        with self.lock:
            if self.last_target is None or joint_state_msg.position != self.last_target.position:
                self.last_target = copy.deepcopy(joint_state_msg)
                self.publish_trajectory()

    def create_trajectory(self, current, target):
        traj = JointTrajectory()
        traj.joint_names = target.name

        duration = 3.0  # seconds
        rate = 10       # Hz
        steps = int(duration * rate)

        for step in range(steps + 1):
            t = step / steps
            point = JointTrajectoryPoint()
            point.time_from_start = rospy.Duration.from_sec(t * duration)
            point.positions = [
                (1 - t) * c + t * tgt
                for c, tgt in zip(current.position, target.position)
            ]
            point.velocities = [0.0] * len(point.positions)
            traj.points.append(point)

        return traj

    def publish_trajectory(self):
        if self.current_joint_state is None or self.last_target is None:
            return

        current = self.current_joint_state
        target = self.last_target

        # Ensure joint positions are aligned
        joint_positions = []
        for name in target.name:
            if name in current.name:
                idx = current.name.index(name)
                joint_positions.append(current.position[idx])
            else:
                joint_positions.append(0.0)

        start_state = JointState(name=target.name, position=joint_positions)

        traj_msg = DisplayTrajectory()
        traj_msg.trajectory_start.joint_state = start_state
        robot_traj = RobotTrajectory()
        robot_traj.joint_trajectory = self.create_trajectory(start_state, target)
        traj_msg.trajectory.append(robot_traj)
        traj_msg.model_id = "robotis_op3"
        self.traj_pub.publish(traj_msg)

    def publish_query_goal_state(self):
        with self.lock:
            if self.last_target is None:
                return

            robot_state = RobotState()
            robot_state.joint_state = self.last_target

            display_state = DisplayRobotState()
            display_state.state = robot_state
            display_state.highlight_links = []

            self.goal_pub.publish(display_state)
