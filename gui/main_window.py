#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main Window for SpokenSense application

This module implements the main application window with tabs for PDF viewing,
TTS controls, and AI chat functionality.
"""
from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QMenuBar, QMenu, QAction, 
    QToolBar, QStatusBar, QLabel,  # Add QLabel here
    QFileDialog, QMessageBox, QVBoxLayout, QWidget,
    QPushButton, QHBoxLayout
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon
import os
from PyQt5.QtWidgets import (QMainWindow, QAction, QFileDialog, QVBoxLayout,
                             QWidget, QDockWidget, QToolBar, QStatusBar, 
                             QMessageBox, QTabWidget, QApplication)
from PyQt5.QtCore import Qt, QSettings, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QKeySequence

from gui.tabs import PDFTabWidget  # Fixed import path

class MainWindow(QMainWindow):
    """Main application window for SpokenSense"""
    
    # Custom signals
    document_loaded = pyqtSignal(str)  # Signal emitted when document is loaded
    
    def __init__(self, config):
        """Initialize the main window
        
        Args:
            config: Application configuration object
        """
        super().__init__()
        
        self.config = config or {}
        self.settings = QSettings("SpokenSense", "SpokenSense")
        
        # Set window properties
        self.setWindowTitle("SpokenSense - Smart PDF Reader")
        self.setMinimumSize(
            self.config.get('window_width', 1024), 
            self.config.get('window_height', 768)
        )
        
        # Create central widget with tabs
        self.tabs = PDFTabWidget(self, config)
        self.setCentralWidget(self.tabs)
        
        # Connect tab signals
        self.tabs.tab_closed.connect(self._on_tab_closed)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        
        # Create UI elements
        self._create_actions()
        self._create_menu_bar()
        self._create_toolbars()
        self._create_status_bar()
        self._create_dock_widgets()
        
        # Restore window geometry and state
        self._restore_settings()
        
        # Set up status update timer
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(1000)  # Update every second
        
        # Show welcome message
        self.status_bar.showMessage("Welcome to SpokenSense! Open a PDF to get started.", 3000)
        # Restore maximized state
        if self.settings.value("windowMaximized", False, type=bool):
            self.showMaximized()
    def _create_actions(self):
        """Create application actions"""
        # File actions
        self.open_action = QAction("&Open PDF...", self)
        self.open_action.setShortcut(QKeySequence.Open)
        self.open_action.setStatusTip("Open a PDF file")
        self.open_action.triggered.connect(self.open_pdf)
        
        self.open_recent_menu = self.menuBar().addMenu("Open &Recent")
        self._update_recent_files()
        
        self.close_tab_action = QAction("Close &Tab", self)
        self.close_tab_action.setShortcut(QKeySequence.Close)
        self.close_tab_action.setStatusTip("Close current tab")
        self.close_tab_action.triggered.connect(self.tabs.close_current_tab)
        
        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut(QKeySequence.Quit)
        self.exit_action.setStatusTip("Exit the application")
        self.exit_action.triggered.connect(self.close)
        
        # TTS actions
        self.play_action = QAction(QIcon.fromTheme("media-playback-start"), "Play", self)
        self.play_action.setShortcut(QKeySequence("F5"))
        self.play_action.setStatusTip("Start TTS playback")
        self.play_action.triggered.connect(self.tabs.play_tts)
        
        self.pause_action = QAction(QIcon.fromTheme("media-playback-pause"), "Pause", self)
        self.pause_action.setShortcut(QKeySequence("F6"))
        self.pause_action.setStatusTip("Pause TTS playback")
        self.pause_action.triggered.connect(self.tabs.pause_tts)
        
        self.stop_action = QAction(QIcon.fromTheme("media-playback-stop"), "Stop", self)
        self.stop_action.setShortcut(QKeySequence("F7"))
        self.stop_action.setStatusTip("Stop TTS playback")
        self.stop_action.triggered.connect(self.tabs.stop_tts)
        
        # Edit actions
        self.preferences_action = QAction("&Preferences...", self)
        self.preferences_action.setStatusTip("Configure application settings")
        self.preferences_action.triggered.connect(self.show_preferences)
        
        # View actions
        self.zoom_in_action = QAction("Zoom &In", self)
        self.zoom_in_action.setShortcut(QKeySequence.ZoomIn)
        self.zoom_in_action.triggered.connect(self.tabs.zoom_in)
        
        self.zoom_out_action = QAction("Zoom &Out", self)
        self.zoom_out_action.setShortcut(QKeySequence.ZoomOut)
        self.zoom_out_action.triggered.connect(self.tabs.zoom_out)
        
        self.reset_zoom_action = QAction("&Reset Zoom", self)
        self.reset_zoom_action.setShortcut("Ctrl+0")
        self.reset_zoom_action.triggered.connect(self.tabs.reset_zoom)
    
    def _create_menu_bar(self):
        """Create the application menu bar"""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self.open_action)
        file_menu.addMenu(self.open_recent_menu)
        file_menu.addSeparator()
        file_menu.addAction(self.close_tab_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)
        
        # Edit menu
        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction(self.preferences_action)
        
        # View menu
        view_menu = menu_bar.addMenu("&View")
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        view_menu.addAction(self.reset_zoom_action)
        
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
        
        documentation_action = QAction("&Documentation", self)
        documentation_action.triggered.connect(self.show_documentation)
        help_menu.addAction(documentation_action)
    
    def _create_toolbars(self):
        """Create application toolbars"""
        # File toolbar
        file_toolbar = self.addToolBar("File")
        file_toolbar.setObjectName("FileToolbar")
        file_toolbar.addAction(self.open_action)
        file_toolbar.setMovable(False)
        
        # TTS toolbar
        tts_toolbar = self.addToolBar("TTS Controls")
        tts_toolbar.setObjectName("TTSToolbar")
        tts_toolbar.addAction(self.play_action)
        tts_toolbar.addAction(self.pause_action)
        tts_toolbar.addAction(self.stop_action)
        tts_toolbar.setMovable(False)
        
        # View toolbar
        view_toolbar = self.addToolBar("View")
        view_toolbar.setObjectName("ViewToolbar")
        view_toolbar.addAction(self.zoom_in_action)
        view_toolbar.addAction(self.zoom_out_action)
        view_toolbar.setMovable(False)
    
    def _create_status_bar(self):
        """Create the status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Add permanent widgets to status bar
        self.page_info_label = QLabel("No document")
        self.status_bar.addPermanentWidget(self.page_info_label)
        
        self.tts_status_label = QLabel("TTS: Stopped")
        self.status_bar.addPermanentWidget(self.tts_status_label)
    
    def _create_dock_widgets(self):
        """Create dock widgets for additional panels"""
        # This is where you'd add AI chat panel, document outline, etc.
        pass
    
    def _restore_settings(self):
        """Restore window settings from previous session"""
        try:
            if self.settings.contains("geometry"):
                self.restoreGeometry(self.settings.value("geometry"))
            if self.settings.contains("windowState"):
                self.restoreState(self.settings.value("windowState"))
        except Exception as e:
            print(f"Warning: Could not restore window settings: {e}")
    
    def _save_settings(self):
        """Save current window settings"""
        try:
            self.settings.setValue("geometry", self.saveGeometry())
            self.settings.setValue("windowState", self.saveState())
        except Exception as e:
            print(f"Warning: Could not save window settings: {e}")
    
    def _update_recent_files(self):
        """Update the recent files menu"""
        self.open_recent_menu.clear()
        recent_files = self.settings.value("recentFiles", [])
        
        if recent_files:
            for file_path in recent_files:
                if os.path.exists(file_path):
                    action = QAction(os.path.basename(file_path), self)
                    action.setData(file_path)
                    action.triggered.connect(self._open_recent_file)
                    self.open_recent_menu.addAction(action)
            self.open_recent_menu.addSeparator()
            
        clear_action = QAction("Clear Recent Files", self)
        clear_action.triggered.connect(self._clear_recent_files)
        self.open_recent_menu.addAction(clear_action)
    
    def _add_to_recent_files(self, file_path):
        """Add file to recent files list"""
        recent_files = self.settings.value("recentFiles", [])
        if file_path in recent_files:
            recent_files.remove(file_path)
        recent_files.insert(0, file_path)
        recent_files = recent_files[:10]  # Keep only last 10
        self.settings.setValue("recentFiles", recent_files)
        self._update_recent_files()
    
    def _open_recent_file(self):
        """Open a recent file"""
        action = self.sender()
        if action:
            file_path = action.data()
            if os.path.exists(file_path):
                self.tabs.open_pdf(file_path)
            else:
                QMessageBox.warning(self, "File Not Found", 
                                  f"The file {file_path} could not be found.")
                # Remove from recent files
                recent_files = self.settings.value("recentFiles", [])
                if file_path in recent_files:
                    recent_files.remove(file_path)
                    self.settings.setValue("recentFiles", recent_files)
                    self._update_recent_files()
    
    def _clear_recent_files(self):
        """Clear the recent files list"""
        self.settings.setValue("recentFiles", [])
        self._update_recent_files()
    
    def open_pdf(self):
        """Open a PDF file"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                "Open PDF", 
                self.settings.value("lastOpenDir", ""),
                "PDF Files (*.pdf);;All Files (*)"
            )
            
            if file_path:
                # Save the directory for next time
                self.settings.setValue("lastOpenDir", os.path.dirname(file_path))
                
                # Open the PDF
                self.tabs.open_pdf(file_path)
                
                # Add to recent files
                self._add_to_recent_files(file_path)
                
                # Emit signal
                self.document_loaded.emit(file_path)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open PDF file:\n{str(e)}")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About SpokenSense",
            """
            <h3>SpokenSense</h3>
            <p>A Smart Offline PDF Reader with Voice Playback and Local AI Chat Assistant</p>
            <p><b>Version:</b> 1.0.0</p>
            <p><b>Features:</b></p>
            <ul>
                <li>Offline PDF reading with word-level highlighting</li>
                <li>Text-to-Speech with synchronized playback</li>
                <li>Local AI assistant with RAG capabilities</li>
                <li>Multi-tab interface for multiple documents</li>
                <li>Privacy-focused - all processing done locally</li>
            </ul>
            <p>© 2024 SpokenSense Team</p>
            """
        )
    
    def show_documentation(self):
        """Show documentation"""
        QMessageBox.information(
            self,
            "Documentation",
            """
            <h3>SpokenSense Documentation</h3>
            <p><b>Getting Started:</b></p>
            <ol>
                <li>Open a PDF file using File → Open PDF</li>
                <li>Use the Play button or F5 to start TTS playback</li>
                <li>Ask questions about the document using the AI chat panel</li>
                <li>Navigate between pages using the Previous/Next buttons</li>
            </ol>
            <p><b>Keyboard Shortcuts:</b></p>
            <ul>
                <li>Ctrl+O: Open PDF</li>
                <li>Ctrl+W: Close Tab</li>
                <li>F5: Play/Pause TTS</li>
                <li>F7: Stop TTS</li>
                <li>Ctrl++: Zoom In</li>
                <li>Ctrl+-: Zoom Out</li>
                <li>Ctrl+0: Reset Zoom</li>
            </ul>
            """
        )
    
    def show_preferences(self):
        """Show preferences dialog"""
        QMessageBox.information(self, "Preferences", 
                              "Preferences dialog would appear here.\n"
                              "Configure TTS settings, AI models, and appearance.")
    
    def _on_tab_closed(self, index):
        """Handle tab closed event"""
        if self.tabs.count() == 0:
            self.status_bar.showMessage("No documents open", 2000)
    
    def _on_tab_changed(self, index):
        """Handle tab changed event"""
        self._update_status()
    
    def _update_status(self):
        """Update status bar information"""
        try:
            current_widget = self.tabs.currentWidget()
            if current_widget and hasattr(current_widget, 'current_page'):
                total_pages = current_widget.pdf_reader.get_page_count() if hasattr(current_widget, 'pdf_reader') and current_widget.pdf_reader else "?"
                page_info = f"Page {current_widget.current_page + 1} of {total_pages}"
                self.page_info_label.setText(page_info)
            
            # Update TTS status (this would need to be connected to actual TTS state)
            # For now, we'll just show a static message
            # self.tts_status_label.setText("TTS: Playing" if tts_playing else "TTS: Stopped")
            
        except Exception as e:
            print(f"Warning: Could not update status: {e}")
    
    def closeEvent(self, event):
        """Handle window close event"""
        try:
            # Save window state
            self._save_settings()
            
            # Save current tabs state
            self.tabs.save_state()
            
            # Close all tabs properly
            if not self.tabs.close_all_tabs():
                event.ignore()
                return
            
            # Accept the close event
            event.accept()
            
        except Exception as e:
            print(f"Error during close: {e}")
            event.accept()  # Still close to avoid hanging
    def set_theme(self, theme_name):
        """Set application theme"""
        if theme_name == "dark":
            # Apply dark theme stylesheet
            self.setStyleSheet("""
                QMainWindow { background-color: #2b2b2b; color: #ffffff; }
                QMenuBar { background-color: #3c3f41; color: #ffffff; }
                QMenuBar::item { background: transparent; }
                QMenuBar::item:selected { background: #4b6eaf; }
                QToolBar { background-color: #3c3f41; border: none; }
                QPushButton { background-color: #4c5052; color: #ffffff; border: 1px solid #5e6060; }
                QPushButton:hover { background-color: #4b6eaf; }
            """)
        else:
            self.setStyleSheet("")  # Reset to default
    