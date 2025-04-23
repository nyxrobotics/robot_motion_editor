#!/usr/bin/env python3
import sys

import rospy
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

from robot_motion_editor.gui.main_window import MainWindow


def main():
    # Initialize the ROS node
    rospy.init_node("robot_motion_editor")

    # Initialize Qt application
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    # Periodically check if ROS is shutting down and quit the Qt app
    timer = QTimer()
    timer.timeout.connect(lambda: app.quit() if rospy.is_shutdown() else None)
    timer.start(100)  # Check every 100 milliseconds

    # Start the Qt event loop
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
