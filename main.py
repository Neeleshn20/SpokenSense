#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SpokenSense - A Smart Offline PDF Reader with Voice Playback and Local AI Chat Assistant

This is the main entry point for the SpokenSense application.
It initializes the GUI and connects all the components together.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow
from config.config import Config


def main():
    """Main entry point for the application"""
    # Load configuration
    config = Config()
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("SpokenSense")
    app.setOrganizationName("SpokenSense")
    
    # Create and show main window
    main_window = MainWindow(config)
    main_window.show()
    
    # Start event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()