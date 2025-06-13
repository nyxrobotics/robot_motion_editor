import rospy
from sensor_msgs.msg import JointState


class InitialPoseCommander:
    def __init__(self, trajectory_commander):
        self.trajectory_commander = trajectory_commander
        self.start_pose = None
        self.goal_pose = None
        self.duration = 1.0

    def set_duration(self, duration: float):
        self.duration = duration

    def set_start_pose(self, joint_state: JointState):
        self.start_pose = joint_state
        if self.goal_pose is None:
            self.goal_pose = joint_state
        self.send_joint_state(self.start_pose)

    def set_goal_pose(self, joint_state: JointState):
        if self.goal_pose is None or joint_state.position != self.goal_pose.position:
            self.goal_pose = joint_state
            if self.start_pose is None:
                self.start_pose = joint_state
            self.send_state2state(self.start_pose, self.goal_pose)

    def get_goal_pose(self):
        return self.goal_pose

    def send_joint_state(self, joint_state: JointState):
        self.trajectory_commander.send_joint_state(joint_state, duration=self.duration)

    def send_state2state(self, start: JointState, end: JointState):
        self.trajectory_commander.send_state2state(start, end, duration=self.duration)
