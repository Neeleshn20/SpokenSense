#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main Window for SpokenSense application

This module implements the main application window with tabs for PDF viewing,
TTS controls, and AI chat functionality.
"""

from PyQt5.QtWidgets import (QMainWindow, QAction, QFileDialog, QVBoxLayout,
                             QWidget, QDockWidget, QToolBar, QStatusBar, QMessageBox)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QIcon

from .tabs import PDFTabWidget


class MainWindow(QMainWindow):
    """Main application window for SpokenSense"""
    
    def __init__(self, config):
        """Initialize the main window
        
        Args:
            config: Application configuration object
        """
        super().__init__()
        
        self.config = config
        self.settings = QSettings("SpokenSense", "SpokenSense")
        
        self.setWindowTitle("SpokenSense - Smart PDF Reader")
        self.setMinimumSize(1024, 768)
        
        # Create central widget with tabs
        self.tabs = PDFTabWidget(self, config)
        self.setCentralWidget(self.tabs)
        
        # Create UI elements
        self._create_actions()
        self._create_menu_bar()
        self._create_toolbars()
        self._create_status_bar()
        
        # Restore window geometry
        self._restore_settings()
    
    def _create_actions(self):
        """Create application actions"""
        # File actions
        self.open_action = QAction("&Open PDF...", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.open_pdf)
        
        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.close)
        
        # TTS actions
        self.play_action = QAction("Play", self)
        self.play_action.setShortcut("F5")
        self.play_action.triggered.connect(self.tabs.play_tts)
        
        self.pause_action = QAction("Pause", self)
        self.pause_action.setShortcut("F6")
        self.pause_action.triggered.connect(self.tabs.pause_tts)
        
        self.stop_action = QAction("Stop", self)
        self.stop_action.setShortcut("F7")
        self.stop_action.triggered.connect(self.tabs.stop_tts)
    
    def _create_menu_bar(self):
        """Create the application menu bar"""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self.open_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)
        
        # TTS menu
        tts_menu = menu_bar.addMenu("&TTS")
        tts_menu.addAction(self.play_action)
        tts_menu.addAction(self.pause_action)
        tts_menu.addAction(self.stop_action)
        
        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def _create_toolbars(self):
        """Create application toolbars"""
        # File toolbar
        file_toolbar = QToolBar("File")
        file_toolbar.addAction(self.open_action)
        self.addToolBar(file_toolbar)
        
        # TTS toolbar
        tts_toolbar = QToolBar("TTS Controls")
        tts_toolbar.addAction(self.play_action)
        tts_toolbar.addAction(self.pause_action)
        tts_toolbar.addAction(self.stop_action)
        self.addToolBar(tts_toolbar)
    
    def _create_status_bar(self):
        """Create the status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _restore_settings(self):
        """Restore window settings from previous session"""
        if self.settings.contains("geometry"):
            self.restoreGeometry(self.settings.value("geometry"))
        if self.settings.contains("windowState"):
            self.restoreState(self.settings.value("windowState"))
    
    def open_pdf(self):
        """Open a PDF file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF", "", "PDF Files (*.pdf)"
        )
        
        if file_path:
            self.tabs.open_pdf(file_path)
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About SpokenSense",
            "<h3>SpokenSense</h3>"
            "<p>A Smart Offline PDF Reader with Voice Playback and Local AI Chat Assistant</p>"
            "<p>Version 0.1.0</p>"
        )
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Save window state
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        
        # Save current tabs state
        self.tabs.save_state()
        
        # Accept the close event
        event.accept()