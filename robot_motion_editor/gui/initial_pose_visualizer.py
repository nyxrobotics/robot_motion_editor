import copy
import threading

import rospy
from moveit_msgs.msg import DisplayTrajectory
from moveit_msgs.msg import RobotState
from moveit_msgs.msg import RobotTrajectory
from sensor_msgs.msg import JointState
from std_msgs.msg import Header
from trajectory_msgs.msg import JointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint


class InitialPoseVisualizer:
    def __init__(self, joint_names):
        self.joint_names = joint_names
        self.lock = threading.Lock()
        self.current_joint_state = None
        self.last_target = None
        self.updated_target = None

        self.traj_pub = rospy.Publisher("/move_group/display_planned_path", DisplayTrajectory, queue_size=1)
        self.joint_state_sub = rospy.Subscriber("/joint_states", JointState, self.joint_state_callback)

        self.timer = rospy.Timer(rospy.Duration(3.0), self.timer_callback)

    def joint_state_callback(self, msg):
        with self.lock:
            self.current_joint_state = msg

    def update_target_pose(self, joint_state_msg):
        with self.lock:
            if self.last_target is None or joint_state_msg.position != self.last_target.position:
                self.updated_target = joint_state_msg
                self.last_target = copy.deepcopy(joint_state_msg)

    def create_trajectory(self, current, target):
        traj = JointTrajectory()
        traj.header = Header()
        traj.header.stamp = rospy.Time.now()
        traj.joint_names = target.name

        p = JointTrajectoryPoint()
        p.positions = target.position
        p.velocities = [0.0] * len(p.positions)
        p.time_from_start = rospy.Duration(3.0)
        traj.points.append(p)

        return traj

    def timer_callback(self, event):
        with self.lock:
            if self.current_joint_state is None or self.last_target is None:
                return

            current = self.current_joint_state
            target = self.last_target

            joint_positions = []
            for name in target.name:
                if name in current.name:
                    index = current.name.index(name)
                    joint_positions.append(current.position[index])
                else:
                    joint_positions.append(0.0)

            start_state = JointState(name=target.name, position=joint_positions)

            traj_msg = DisplayTrajectory()
            traj_msg.trajectory_start = start_state
            robot_traj = RobotTrajectory()
            robot_traj.joint_trajectory = self.create_trajectory(start_state, target)
            traj_msg.trajectory.append(robot_traj)

            self.traj_pub.publish(traj_msg)
