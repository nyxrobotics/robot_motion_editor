import xml.etree.ElementTree as ET

import rospy


def get_transmission_joints():
    xml_string = rospy.get_param("/robot_description")
    root = ET.fromstring(xml_string)
    joints = []
    for transmission in root.findall("transmission"):
        joint_elem = transmission.find("joint")
        if joint_elem is not None and 'name' in joint_elem.attrib:
            joints.append(joint_elem.attrib["name"])
    return joints
