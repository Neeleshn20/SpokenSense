#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Tab Widget for SpokenSense
This module implements a tabbed interface for managing multiple PDF documents,
including PDF viewing, TTS controls, and AI chat functionality.
"""
import os
import json
import threading
from PyQt5.QtWidgets import (QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
                             QSplitter, QLabel, QPushButton, QTextEdit,
                             QScrollArea, QFrame, QLineEdit, QProgressBar, QMenu)
from PyQt5.QtCore import Qt, QSettings, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont, QTextCursor
from pdf.reader import PDFReader
from tts.coqui_tts import CoquiTTS
from ai.llm_qa import LLMQA
from gui.highlight import PDFViewWidget  # Fixed import path

class PDFTabWidget(QTabWidget):
    """Tab widget for managing multiple PDF documents"""
    tab_closed = pyqtSignal(int)  # Signal emitted when tab is closed

    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config or {}
        self.settings = QSettings("SpokenSense", "SpokenSense")
        self.pdf_tabs = {}
        self.setTabsClosable(True)
        self.setMovable(True)
        self.tabCloseRequested.connect(self.close_tab)
        # Restore tabs from previous session
        self._restore_tabs()
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_tab_context_menu)

    def _show_tab_context_menu(self, position):
        """Show context menu for tabs"""
        menu = QMenu()
        close_action = menu.addAction("Close Tab")
        close_action.triggered.connect(lambda: self.close_tab(self.tabAt(position)))
        menu.exec_(self.mapToGlobal(position))

    def _restore_tabs(self):
        """Restore tabs from previous session"""
        user_state_path = os.path.join(self.config.get('data_dir', './data'), 'user_state.json')
        if os.path.exists(user_state_path):
            try:
                with open(user_state_path, 'r') as f:
                    state = json.load(f)
                if 'open_pdfs' in state and isinstance(state['open_pdfs'], list):
                    for pdf_info in state['open_pdfs']:
                        file_path = pdf_info.get('path', '')
                        if os.path.exists(file_path):
                            self.open_pdf(
                                file_path,
                                page=pdf_info.get('page', 0)
                            )
                        else:
                            print(f"Warning: File not found - {file_path}")
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error restoring tabs: {e}")
            except Exception as e:
                print(f"Unexpected error restoring tabs: {e}")

    def save_state(self):
        """Save current tab state"""
        user_state_path = os.path.join(self.config.get('data_dir', './data'), 'user_state.json')
        os.makedirs(os.path.dirname(user_state_path), exist_ok=True)
        state = {
            'open_pdfs': []
        }
        # Save information about currently open PDFs
        for path, tab_info in self.pdf_tabs.items():
            if os.path.exists(path) and hasattr(tab_info['widget'], 'pdf_view'):
                try:
                    current_page = tab_info['widget'].pdf_view.current_page
                    state['open_pdfs'].append({
                        'path': path,
                        'page': current_page
                    })
                except Exception as e:
                    print(f"Warning: Could not save state for {path}: {e}")
        try:
            with open(user_state_path, 'w') as f:
                json.dump(state, f, indent=2)
        except IOError as e:
            print(f"Error saving state: {e}")
        except Exception as e:
            print(f"Unexpected error saving state: {e}")

    def open_pdf(self, file_path, page=0):
        """Open a PDF file in a new tab"""
        if not os.path.exists(file_path):
            print(f"Error: File not found - {file_path}")
            return
        # Check if file is already open
        if file_path in self.pdf_tabs:
            self.setCurrentIndex(self.pdf_tabs[file_path]['index'])
            return
        try:
            # Create new PDF tab
            pdf_tab = PDFTab(self, self.config, file_path, page)
            # Add tab to widget
            tab_index = self.addTab(pdf_tab, os.path.basename(file_path))
            self.setCurrentIndex(tab_index)
            # Store tab reference
            self.pdf_tabs[file_path] = {
                'widget': pdf_tab,
                'index': tab_index
            }
            print(f"Opened PDF: {file_path}")
        except Exception as e:
            print(f"Error opening PDF {file_path}: {e}")

    def close_tab(self, index):
        """Close a specific tab"""
        if index < 0 or index >= self.count():
            return
        tab_widget = self.widget(index)
        # Clean up tab resources
        if hasattr(tab_widget, 'cleanup'):
            try:
                tab_widget.cleanup()
            except Exception as e:
                print(f"Warning: Error during tab cleanup: {e}")
        # Remove tab
        self.removeTab(index)
        # Update tab references
        tab_to_remove = None
        for path, tab_info in list(self.pdf_tabs.items()):
            if tab_info['widget'] == tab_widget:
                tab_to_remove = path
            elif tab_info['index'] > index:
                tab_info['index'] -= 1
        # Remove closed tab from tracking
        if tab_to_remove:
            del self.pdf_tabs[tab_to_remove]
        # Emit signal
        self.tab_closed.emit(index)

    def close_current_tab(self):
        """Close the currently selected tab"""
        current_index = self.currentIndex()
        if current_index >= 0:
            self.close_tab(current_index)

    def close_all_tabs(self):
        """Close all tabs and return True if successful"""
        try:
            # Close all tabs
            while self.count() > 0:
                self.close_tab(0)
            return True
        except Exception as e:
            print(f"Error closing all tabs: {e}")
            return False

    def play_tts(self):
        """Play TTS for current tab"""
        current_tab = self.currentWidget()
        if current_tab and hasattr(current_tab, 'play_tts'):
            current_tab.play_tts()

    def pause_tts(self):
        """Pause TTS for current tab"""
        current_tab = self.currentWidget()
        if current_tab and hasattr(current_tab, 'pause_tts'):
            current_tab.pause_tts()

    def stop_tts(self):
        """Stop TTS for current tab"""
        current_tab = self.currentWidget()
        if current_tab and hasattr(current_tab, 'stop_tts'):
            current_tab.stop_tts()

    def zoom_in(self):
        """Zoom in on current tab"""
        current_tab = self.currentWidget()
        if current_tab and hasattr(current_tab, 'zoom_in'):
            current_tab.zoom_in()

    def zoom_out(self):
        """Zoom out on current tab"""
        current_tab = self.currentWidget()
        if current_tab and hasattr(current_tab, 'zoom_out'):
            current_tab.zoom_out()

    def reset_zoom(self):
        """Reset zoom on current tab"""
        current_tab = self.currentWidget()
        if current_tab and hasattr(current_tab, 'reset_zoom'):
            current_tab.reset_zoom()

class PDFTab(QWidget):
    """Widget for a single PDF tab"""
    # Signal for thread-safe UI update after document processing
    _document_processed_signal = pyqtSignal(bool, str)

    def __init__(self, parent, config, file_path, page=0):
        super().__init__(parent)
        self.config = config or {}
        self.file_path = file_path
        self.current_page = page
        # Initialize components
        self.pdf_reader = None
        self.tts_engine = None
        self.llm_qa = None
        self.pdf_view = None
        # Initialize UI and components
        self._initialize_components()
        self._setup_ui()
        # Connect the signal for processing completion
        self._document_processed_signal.connect(self._on_document_processed)
        # Process document for AI
        self._process_document_for_ai()

    def _initialize_components(self):
        """Initialize all components"""
        try:
            self.pdf_reader = PDFReader(self.file_path, self.config)
            self.tts_engine = CoquiTTS(self.config)
            self.llm_qa = LLMQA(self.file_path, self.config)
            # Connect AI response signal
            self.llm_qa.answer_ready.connect(self._handle_ai_response)
        except Exception as e:
            print(f"Error initializing components for {self.file_path}: {e}")
            raise

    def _setup_ui(self):
        """Set up the user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)
        # Create main splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(3)
        # PDF viewing area
        pdf_area = self._create_pdf_area()
        splitter.addWidget(pdf_area)
        # Chat area
        chat_area = self._create_chat_area()
        splitter.addWidget(chat_area)
        # Set initial sizes (70% PDF, 30% chat)
        splitter.setSizes([700, 300])
        main_layout.addWidget(splitter)

    def _create_pdf_area(self):
        """Create the PDF viewing area"""
        pdf_area = QWidget()
        pdf_layout = QVBoxLayout(pdf_area)
        pdf_layout.setContentsMargins(0, 0, 0, 0)
        pdf_layout.setSpacing(2)
        # PDF view widget
        self.pdf_view = PDFViewWidget(self, self.pdf_reader, self.tts_engine)
        self.pdf_view.load_page(self.current_page)
        pdf_layout.addWidget(self.pdf_view)
        return pdf_area

    def _create_chat_area(self):
        """Create the chat area"""
        chat_area = QWidget()
        chat_layout = QVBoxLayout(chat_area)
        chat_layout.setContentsMargins(5, 5, 5, 5)
        chat_layout.setSpacing(5)
        # Chat title
        chat_title = QLabel("Document Assistant")
        chat_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        chat_layout.addWidget(chat_title)
        # Chat history
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
        """)
        chat_layout.addWidget(self.chat_history)
        # Progress bar for AI processing
        self.ai_progress = QProgressBar()
        self.ai_progress.setVisible(False)
        self.ai_progress.setRange(0, 0)  # Indeterminate
        chat_layout.addWidget(self.ai_progress)
        # Input area
        input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ask a question about this document...")
        self.chat_input.returnPressed.connect(self.send_chat)
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_chat)
        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(self.send_button)
        chat_layout.addLayout(input_layout)
        return chat_area

    # --- REMOVED the first definition of _process_document_for_ai (lines ~217-226) ---

    def _add_chat_message(self, sender, message):
        """Add a message to the chat history"""
        cursor = self.chat_history.textCursor()
        cursor.movePosition(QTextCursor.End)
        if sender == "System":
            formatted_message = f'<div style="color: #6c757d; font-style: italic;"><b>{sender}:</b> {message}</div>'
        elif sender == "You":
            formatted_message = f'<div style="color: #007bff;"><b>{sender}:</b> {message}</div>'
        elif sender == "AI":
            formatted_message = f'<div style="color: #28a745;"><b>{sender}:</b> {message}</div>'
        else:
            formatted_message = f'<b>{sender}:</b> {message}'
        cursor.insertHtml(formatted_message + "<br><br>")
        self.chat_history.setTextCursor(cursor)
        self.chat_history.ensureCursorVisible()

    def play_tts(self):
        """Play TTS"""
        if self.pdf_view:
            self.pdf_view.play_tts()

    def pause_tts(self):
        """Pause TTS"""
        if self.pdf_view:
            self.pdf_view.pause_tts()

    def stop_tts(self):
        """Stop TTS"""
        if self.pdf_view:
            self.pdf_view.stop_tts()

    def zoom_in(self):
        """Zoom in on PDF"""
        if self.pdf_view and hasattr(self.pdf_view.pdf_display, 'zoom_in'):
            self.pdf_view.pdf_display.zoom_in()

    def zoom_out(self):
        """Zoom out on PDF"""
        if self.pdf_view and hasattr(self.pdf_view.pdf_display, 'zoom_out'):
            self.pdf_view.pdf_display.zoom_out()

    def reset_zoom(self):
        """Reset PDF zoom"""
        if self.pdf_view and hasattr(self.pdf_view.pdf_display, 'reset_zoom'):
            self.pdf_view.pdf_display.reset_zoom()

    # --- KEEPING and FIXING the second definition of _process_document_for_ai ---
    def _process_document_for_ai(self):
        """Process document for AI functionality with progress"""
        self._add_chat_message("System", "Processing document for AI assistant...")
        def process_in_thread():
            try:
                chunks = self.pdf_reader.get_document_chunks()
                if chunks:
                    # ----------------------------------------------------
                    # FIXED: Pass the correct 'chunks' list, not 'self.config'
                    # ----------------------------------------------------
                    self.llm_qa.process_document(chunks)
                    # ----------------------------------------------------
                    # Use signal to update UI from thread
                    self._document_processed_signal.emit(True, "Document processing complete.")
                else:
                    self._document_processed_signal.emit(False, "No text found in document.")
            except Exception as e:
                # Emit the error via signal for thread-safe UI update
                self._document_processed_signal.emit(False, f"Error processing document: {str(e)}")

        # Start the processing thread
        thread = threading.Thread(target=process_in_thread)
        thread.daemon = True
        thread.start()

    def _on_document_processed(self, success, message):
        """Slot to handle the document processed signal and update UI."""
        # Hide progress bar
        self.ai_progress.setVisible(False)
        # Add the system message to the chat
        self._add_chat_message("System", message)
        # Potentially enable chat input here if processing was successful
        # or handle the error state. For now, we just log the message in chat.
        if success:
             print(f"Document processing finished successfully for {self.file_path}")
        else:
             print(f"Document processing failed for {self.file_path}: {message}")

    def send_chat(self):
        """Send chat message to AI"""
        query = self.chat_input.text().strip()
        if not query:
            return
        # Clear input and disable controls
        self.chat_input.clear()
        self.chat_input.setEnabled(False)
        self.send_button.setEnabled(False)
        self.send_button.setText("Processing...")
        self.ai_progress.setVisible(True)
        # Add user message to chat
        self._add_chat_message("You", query)
        try:
            # Send query to AI (non-blocking)
            self.llm_qa.ask(query, page=self.pdf_view.current_page if self.pdf_view else None)
        except Exception as e:
            print(f"Error sending chat query: {e}")
            self._add_chat_message("Error", "Failed to send your question. Please try again.")
            self._reset_chat_controls()

    def _handle_ai_response(self, answer):
        """Handle AI response (slot for answer_ready signal)"""
        # Reset controls
        self._reset_chat_controls()
        # Add AI response to chat
        self._add_chat_message("AI", answer)
        # Auto-scroll to bottom
        scrollbar = self.chat_history.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _reset_chat_controls(self):
        """Reset chat input controls"""
        self.chat_input.setEnabled(True)
        self.send_button.setEnabled(True)
        self.send_button.setText("Send")
        self.ai_progress.setVisible(False)

    def cleanup(self):
        """Clean up resources"""
        try:
            # Stop TTS
            self.stop_tts()
            # Clean up TTS engine
            if hasattr(self, 'tts_engine') and self.tts_engine:
                self.tts_engine.cleanup()
            # Clean up AI components
            if hasattr(self, 'llm_qa') and self.llm_qa:
                self.llm_qa.cleanup()
            # Clean up PDF reader
            if hasattr(self, 'pdf_reader') and self.pdf_reader:
                self.pdf_reader.cleanup()
        except Exception as e:
            print(f"Warning: Error during tab cleanup: {e}")

    # --- REMOVED the duplicate _handle_ai_response definition ---
    # The correct one (for answer_ready signal) is sufficient.
    # The one for _document_processed_signal is _on_document_processed.
