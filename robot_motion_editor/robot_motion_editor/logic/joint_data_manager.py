
class JointDataManager:
    def __init__(self, joint_names=None, joint_limits=None, available_variables=None):
        self.joint_names = joint_names or []
        self.joint_limits = joint_limits or {}
        self.available_variables = available_variables or []

    def set_joint_names(self, joint_names):
        self.joint_names = joint_names

    def get_joint_names(self):
        return self.joint_names

    def set_joint_limits(self, joint_limits):
        self.joint_limits = joint_limits

    def get_joint_limits(self):
        return self.joint_limits

    def set_available_variables(self, variables):
        self.available_variables = variables

    def get_available_variables(self):
        return self.available_variables

    def get_joint_limit(self, joint_name):
        return self.joint_limits.get(joint_name, (-3.14, 3.14))  # default to ±π

    def is_valid_joint(self, joint_name):
        return joint_name in self.joint_names
