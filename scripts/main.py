#!/usr/bin/env python3
import sys

import rospy
from PyQt5.QtWidgets import QApplication

from robot_motion_editor.gui.main_window import MainWindow

if __name__ == '__main__':
    rospy.init_node('robot_motion_editor')
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
