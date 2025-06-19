import threading

import rospy
from sensor_msgs.msg import JointState


class JointStateSubscriber:
    def __init__(self, topic="/joint_states"):
        self._lock = threading.Lock()
        self._joint_state = None
        self._subscriber = rospy.Subscriber(topic, JointState, self._callback)
        rospy.loginfo(f"[JointStateSubscriber] Subscribed to {topic}")

    def _callback(self, msg):
        with self._lock:
            self._joint_state = msg

    def get_joint_state(self):
        with self._lock:
            return self._joint_state

    def reset_joint_state(self):
        with self._lock:
            self._joint_state = None

    def wait_for_joint_state(self, timeout=5.0):
        start_time = rospy.Time.now()
        timeout_duration = rospy.Duration(timeout)
        self.reset_joint_state
        while rospy.Time.now() - start_time < timeout_duration:
            if self._joint_state is not None:
                with self._lock:
                    return self._joint_state
            rospy.sleep(0.1)
        return None
