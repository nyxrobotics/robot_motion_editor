from urdf_parser_py.urdf import URDF


def get_transmission_joints():
    robot = URDF.from_parameter_server()
    joints = []
    for t in robot.transmissions:
        if hasattr(t, 'joint') and t.joint:
            joints.append(t.joint.name)
    return joints
