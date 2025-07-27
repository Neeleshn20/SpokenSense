#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SpokenSense - A Smart Offline PDF Reader with Voice Playback and Local AI Chat Assistant

This is the main entry point for the SpokenSense application.
It initializes the GUI and connects all the components together.
"""

import sys
import os
import logging
from PyQt5.QtWidgets import QApplication

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from gui.main_window import MainWindow
    from config.config import Config
except ImportError as e:
    logger.critical(f"Failed to import required modules: {e}")
    print(f"Error: Missing required modules. Please ensure all dependencies are installed.")
    print(f"Missing module: {e}")
    sys.exit(1)

def main():
    """Main entry point for the application"""
    logger.info("Starting SpokenSense application...")

    try:
        # Load configuration
        config = Config()
        logger.info("Configuration loaded successfully")

    except Exception as e:
        logger.critical(f"Failed to load configuration: {e}")
        print(f"Error: Could not load configuration: {e}")
        sys.exit(1)

    try:
        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName("SpokenSense")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("SpokenSense")
        app.setOrganizationDomain("spoken-sense.example.com")

        logger.info("QApplication initialized")

    except Exception as e:
        logger.critical(f"Failed to initialize QApplication: {e}")
        print(f"Error: Could not initialize the application framework: {e}")
        sys.exit(1)

    try:
        # Create and show main window
        logger.info("Creating main window...")
        main_window = MainWindow(config)

        # Show the window
        main_window.show()
        logger.info("Main window displayed")

    except Exception as e:
        logger.critical(f"Failed to create or show main window: {e}", exc_info=True)
        print(f"Error: Could not start the main application window: {e}")
        sys.exit(1)

    try:
        # Start event loop
        logger.info("Entering application event loop")
        exit_code = app.exec_()
        logger.info(f"Application exited with code {exit_code}")
        sys.exit(exit_code)

    except Exception as e:
        logger.critical(f"Unexpected error in event loop: {e}", exc_info=True)
        print(f"Error: An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()