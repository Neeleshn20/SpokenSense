#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF Tab Widget for SpokenSense

This module implements a tabbed interface for managing multiple PDF documents,
including PDF viewing, TTS controls, and AI chat functionality.
"""

import os
import json
from PyQt5.QtWidgets import (QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
                             QSplitter, QLabel, QPushButton, QTextEdit,
                             QScrollArea, QFrame, QLineEdit)
from PyQt5.QtCore import Qt, QSettings, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QFont

from pdf.reader import PDFReader
from tts.coqui_tts import CoquiTTS
from ai.llm_qa import LLMQA
from .highlight import PDFViewWidget


class PDFTabWidget(QTabWidget):
    """Tab widget for managing multiple PDF documents"""
    
    def __init__(self, parent, config):
        """Initialize the tab widget
        
        Args:
            parent: Parent widget
            config: Application configuration
        """
        super().__init__(parent)
        
        self.config = config
        self.settings = QSettings("SpokenSense", "SpokenSense")
        self.pdf_tabs = {}
        
        # Set up tab widget
        self.setTabsClosable(True)
        self.setMovable(True)
        self.tabCloseRequested.connect(self.close_tab)
        
        # Restore tabs from previous session
        self._restore_tabs()
    
    def _restore_tabs(self):
        """Restore tabs from previous session"""
        user_state_path = os.path.join(self.config.get('data_dir'), 'user_state.json')
        
        if os.path.exists(user_state_path):
            try:
                with open(user_state_path, 'r') as f:
                    state = json.load(f)
                    
                if 'open_pdfs' in state and isinstance(state['open_pdfs'], list):
                    for pdf_info in state['open_pdfs']:
                        if os.path.exists(pdf_info.get('path', '')):
                            self.open_pdf(
                                pdf_info['path'],
                                page=pdf_info.get('page', 0)
                            )
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error restoring tabs: {e}")
    
    def save_state(self):
        """Save current tabs state"""
        user_state_path = os.path.join(self.config.get('data_dir'), 'user_state.json')
        os.makedirs(os.path.dirname(user_state_path), exist_ok=True)
        
        state = {
            'open_pdfs': []
        }
        
        for path, tab_info in self.pdf_tabs.items():
            if os.path.exists(path):
                state['open_pdfs'].append({
                    'path': path,
                    'page': tab_info['widget'].current_page
                })
        
        try:
            with open(user_state_path, 'w') as f:
                json.dump(state, f)
        except IOError as e:
            print(f"Error saving state: {e}")
    
    def open_pdf(self, file_path, page=0):
        """Open a PDF file in a new tab
        
        Args:
            file_path: Path to the PDF file
            page: Page number to open (default: 0)
        """
        if file_path in self.pdf_tabs:
            # PDF already open, switch to its tab
            self.setCurrentIndex(self.pdf_tabs[file_path]['index'])
            return
        
        # Create a new tab for the PDF
        pdf_tab = PDFTab(self, self.config, file_path, page)
        
        # Add the tab
        tab_index = self.addTab(pdf_tab, os.path.basename(file_path))
        self.setCurrentIndex(tab_index)
        
        # Store tab info
        self.pdf_tabs[file_path] = {
            'widget': pdf_tab,
            'index': tab_index
        }
    
    def close_tab(self, index):
        """Close a tab
        
        Args:
            index: Index of the tab to close
        """
        # Get the tab widget
        tab_widget = self.widget(index)
        
        # Clean up resources
        if hasattr(tab_widget, 'cleanup'):
            tab_widget.cleanup()
        
        # Remove the tab
        self.removeTab(index)
        
        # Update tab indices
        for path, tab_info in list(self.pdf_tabs.items()):
            if tab_info['widget'] == tab_widget:
                del self.pdf_tabs[path]
            elif tab_info['index'] > index:
                tab_info['index'] -= 1
    
    def play_tts(self):
        """Play TTS for the current tab"""
        current_tab = self.currentWidget()
        if current_tab and hasattr(current_tab, 'play_tts'):
            current_tab.play_tts()
    
    def pause_tts(self):
        """Pause TTS for the current tab"""
        current_tab = self.currentWidget()
        if current_tab and hasattr(current_tab, 'pause_tts'):
            current_tab.pause_tts()
    
    def stop_tts(self):
        """Stop TTS for the current tab"""
        current_tab = self.currentWidget()
        if current_tab and hasattr(current_tab, 'stop_tts'):
            current_tab.stop_tts()


class PDFTab(QWidget):
    """Widget for a single PDF tab"""
    
    def __init__(self, parent, config, file_path, page=0):
        """Initialize the PDF tab
        
        Args:
            parent: Parent widget
            config: Application configuration
            file_path: Path to the PDF file
            page: Page number to open (default: 0)
        """
        super().__init__(parent)
        
        self.config = config
        self.file_path = file_path
        self.current_page = page
        
        # Initialize components
        self.pdf_reader = PDFReader(file_path, config)
        self.tts_engine = CoquiTTS(config)
        self.llm_qa = LLMQA(file_path, config)
        
        # Set up UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the tab UI"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create splitter for PDF view and chat
        splitter = QSplitter(Qt.Horizontal)
        
        # PDF view area
        pdf_area = QWidget()
        pdf_layout = QVBoxLayout(pdf_area)
        pdf_layout.setContentsMargins(0, 0, 0, 0)
        
        # PDF view widget
        self.pdf_view = PDFViewWidget(self, self.pdf_reader, self.tts_engine)
        self.pdf_view.load_page(self.current_page)
        pdf_layout.addWidget(self.pdf_view)
        
        # TTS controls
        tts_controls = QWidget()
        tts_layout = QHBoxLayout(tts_controls)
        
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.play_tts)
        
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.pause_tts)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_tts)
        
        tts_layout.addWidget(self.play_button)
        tts_layout.addWidget(self.pause_button)
        tts_layout.addWidget(self.stop_button)
        
        pdf_layout.addWidget(tts_controls)
        
        # Chat area
        chat_area = QWidget()
        chat_layout = QVBoxLayout(chat_area)
        
        chat_layout.addWidget(QLabel("Ask about this document:"))
        
        # Chat history
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        chat_layout.addWidget(self.chat_history)
        
        # Chat input
        chat_input_layout = QHBoxLayout()
        
        self.chat_input = QLineEdit()
        self.chat_input.returnPressed.connect(self.send_chat)
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_chat)
        
        chat_input_layout.addWidget(self.chat_input)
        chat_input_layout.addWidget(self.send_button)
        
        chat_layout.addLayout(chat_input_layout)
        
        # Add widgets to splitter
        splitter.addWidget(pdf_area)
        splitter.addWidget(chat_area)
        
        # Set initial sizes (70% PDF, 30% chat)
        splitter.setSizes([700, 300])
        
        main_layout.addWidget(splitter)
    
    def play_tts(self):
        """Play TTS for the current page"""
        self.pdf_view.play_tts()
    
    def pause_tts(self):
        """Pause TTS playback"""
        self.pdf_view.pause_tts()
    
    def stop_tts(self):
        """Stop TTS playback"""
        self.pdf_view.stop_tts()
    
    def send_chat(self):
        """Send a chat message to the AI assistant"""
        query = self.chat_input.text().strip()
        if not query:
            return
        
        # Clear input
        self.chat_input.clear()
        
        # Add user message to chat history
        self.chat_history.append(f"<b>You:</b> {query}")
        
        # Get response from AI
        try:
            response = self.llm_qa.ask(query, page=self.pdf_view.current_page)
            
            # Add AI response to chat history
            self.chat_history.append(f"<b>AI:</b> {response}")
            
        except Exception as e:
            self.chat_history.append(f"<b>Error:</b> {str(e)}")
    
    def cleanup(self):
        """Clean up resources"""
        # Stop TTS if playing
        self.stop_tts()
        
        # Clean up other resources
        if hasattr(self, 'tts_engine'):
            self.tts_engine.cleanup()
        
        if hasattr(self, 'llm_qa'):
            self.llm_qa.cleanup()