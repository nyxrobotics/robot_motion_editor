import xml.etree.ElementTree as ET

import rospy


def get_robot_name():
    xml_string = rospy.get_param("/robot_description")
    root = ET.fromstring(xml_string)
    return root.attrib.get("name", "robot_name")


def get_transmission_joints():
    xml_string = rospy.get_param("/robot_description")
    root = ET.fromstring(xml_string)
    joints = []
    for transmission in root.findall("transmission"):
        joint_elem = transmission.find("joint")
        if joint_elem is not None and 'name' in joint_elem.attrib:
            joints.append(joint_elem.attrib["name"])
    return joints


def get_joint_limit(joint_name):
    # Get the URDF XML string from the /robot_description parameter
    xml_string = rospy.get_param("/robot_description")
    root = ET.fromstring(xml_string)

    # Search for the <joint> tag with the matching name
    for joint in root.findall("joint"):
        name = joint.get("name")
        joint_type = joint.get("type")
        if name == joint_name and joint_type != "fixed":
            limit_elem = joint.find("limit")
            if limit_elem is not None:
                try:
                    lower = float(limit_elem.get("lower", "-inf"))
                    upper = float(limit_elem.get("upper", "inf"))
                    return (lower, upper)
                except (TypeError, ValueError):
                    rospy.logwarn(f"Could not parse limits for joint '{joint_name}'")
                    return None
    # If no matching joint or limit was found
    rospy.logwarn(f"Joint '{joint_name}' not found or has no limit.")
    return None
