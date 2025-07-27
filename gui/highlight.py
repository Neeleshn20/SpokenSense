#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF View Widget with Word Highlighting for SpokenSense

This module implements a PDF viewer with word-level highlighting
for synchronization with TTS playback.
"""

import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QScrollArea, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QTimer, QSize
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QPixmap, QImage

class PDFViewWidget(QScrollArea):
    """Widget for displaying PDF with word highlighting"""
    
    def __init__(self, parent, pdf_reader, tts_engine):
        """Initialize the PDF view widget
        
        Args:
            parent: Parent widget
            pdf_reader: PDFReader instance
            tts_engine: TTS engine instance
        """
        super().__init__(parent)
        
        self.pdf_reader = pdf_reader
        self.tts_engine = tts_engine
        self.current_page = 0
        self.total_pages = 0
        self.current_word_index = -1
        self.page_text = None
        self.word_boxes = None
        self.is_playing = False
        self.zoom_factor = 1.0
        # Initialize total pages if reader is available
        if self.pdf_reader:
            self.total_pages = self.pdf_reader.get_page_count()
        
        # Set up UI
        self._setup_ui()
        
        # Connect TTS callbacks if engine is available
        if self.tts_engine:
            self.tts_engine.set_word_callback(self._highlight_word)
    
    
    def zoom_in(self):
        """Zoom in on the page"""
        self.zoom_factor *= 1.1
        self._apply_zoom()

    def zoom_out(self):
        """Zoom out on the page"""
        self.zoom_factor /= 1.1
        self._apply_zoom()

    def reset_zoom(self):
        """Reset zoom to 100%"""
        self.zoom_factor = 1.0
        self._apply_zoom()

    def _apply_zoom(self):
        """Apply current zoom factor"""
        if self.page_image:
            new_width = int(self.page_image.width() * self.zoom_factor)
            new_height = int(self.page_image.height() * self.zoom_factor)
            self.setFixedSize(new_width, new_height)
            self.update()

    def _setup_ui(self):
        """Set up the widget UI"""
        # Main widget and layout
        self.content_widget = QWidget()
        self.setWidget(self.content_widget)
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignCenter)
        
        main_layout = QVBoxLayout(self.content_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.play_button = QPushButton("▶ Play")
        self.play_button.clicked.connect(self._toggle_play)
        self.play_button.setObjectName("playButton")
        
        self.stop_button = QPushButton("⏹ Stop")
        self.stop_button.clicked.connect(self.stop_tts)
        self.stop_button.setObjectName("stopButton")
        
        self.prev_button = QPushButton("◀ Previous")
        self.prev_button.clicked.connect(self._prev_page)
        
        self.page_label = QLabel("No document loaded")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setMinimumWidth(150)
        
        self.next_button = QPushButton("Next ▶")
        self.next_button.clicked.connect(self._next_page)
        
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addStretch()
        control_layout.addWidget(self.prev_button)
        control_layout.addWidget(self.page_label)
        control_layout.addWidget(self.next_button)
        
        main_layout.addLayout(control_layout)
        
        # PDF display
        self.pdf_display = PDFPageWidget(self)
        main_layout.addWidget(self.pdf_display)
        
        # Update button states
        self._update_button_states()
    
    def load_document(self, file_path):
        """Load a PDF document
        
        Args:
            file_path: Path to the PDF file
        """
        try:
            if self.pdf_reader:
                self.pdf_reader.load_document(file_path)
                self.total_pages = self.pdf_reader.get_page_count()
                self.current_page = 0
                self.load_page(0)
                self._update_button_states()
                print(f"Loaded document: {file_path}")
        except Exception as e:
            print(f"Error loading document: {e}")
    
    def load_page(self, page_num):
        """Load a specific page
        
        Args:
            page_num: Page number to load (0-indexed)
        """
        if not self.pdf_reader or page_num < 0 or page_num >= self.total_pages:
            return
        
        try:
            # Stop TTS if playing
            if self.is_playing:
                self.stop_tts()
            
            # Update current page
            self.current_page = page_num
            self.page_label.setText(f"Page {self.current_page + 1} of {self.total_pages}")
            
            # Get page text and word boxes
            page_data = self.pdf_reader.get_page_text_and_boxes(page_num)
            if page_data:
                self.page_text, self.word_boxes = page_data
            else:
                self.page_text, self.word_boxes = "", []
            
            # Update display
            page_image = self.pdf_reader.get_page_image(page_num)
            self.pdf_display.set_page(page_image, self.word_boxes)
            
            # Reset word highlighting
            self.current_word_index = -1
            self._update_button_states()
            
        except Exception as e:
            print(f"Error loading page {page_num}: {e}")
    
    def _prev_page(self):
        """Go to the previous page"""
        if self.current_page > 0:
            self.load_page(self.current_page - 1)
    
    def _next_page(self):
        """Go to the next page"""
        if self.current_page < self.total_pages - 1:
            self.load_page(self.current_page + 1)
    
    def _toggle_play(self):
        """Toggle TTS playback"""
        if self.is_playing:
            self.pause_tts()
        else:
            self.play_tts()
    
    def play_tts(self):
        """Play TTS for the current page"""
        if self.page_text and self.tts_engine:
            try:
                self.is_playing = True
                self.play_button.setText("⏸ Pause")
                self.tts_engine.speak(self.page_text, self.word_boxes)
            except Exception as e:
                print(f"Error starting TTS: {e}")
                self.is_playing = False
                self.play_button.setText("▶ Play")
        else:
            print("No text to speak or TTS engine not available")
    
    def pause_tts(self):
        """Pause TTS playback"""
        if self.tts_engine:
            try:
                self.tts_engine.pause()
                self.is_playing = False
                self.play_button.setText("▶ Play")
            except Exception as e:
                print(f"Error pausing TTS: {e}")
    
    def stop_tts(self):
        """Stop TTS playback"""
        if self.tts_engine:
            try:
                self.tts_engine.stop()
                self.is_playing = False
                self.play_button.setText("▶ Play")
                self.current_word_index = -1
                self.pdf_display.clear_highlight()
            except Exception as e:
                print(f"Error stopping TTS: {e}")
    
    def _highlight_word(self, word_index):
        """Highlight a word during TTS playback
        
        Args:
            word_index: Index of the word to highlight
        """
        if not self.word_boxes or word_index < 0 or word_index >= len(self.word_boxes):
            return
        
        self.current_word_index = word_index
        self.pdf_display.highlight_word(word_index)
        
        # Ensure the highlighted word is visible
        if word_index < len(self.word_boxes):
            word_box = self.word_boxes[word_index]
            self.pdf_display.ensure_visible(word_box)
    
    def _update_button_states(self):
        """Update button enabled states"""
        if not self.pdf_reader or self.total_pages == 0:
            # No document loaded
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
            self.play_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            return
        
        # Update navigation buttons
        self.prev_button.setEnabled(self.current_page > 0)
        self.next_button.setEnabled(self.current_page < self.total_pages - 1)
        
        # Update playback buttons
        self.play_button.setEnabled(bool(self.page_text))
        self.stop_button.setEnabled(self.is_playing)


class PDFPageWidget(QWidget):
    """Widget for displaying a PDF page with word highlighting"""
    
    def __init__(self, parent):
        """Initialize the PDF page widget
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.page_image = None
        self.word_boxes = None
        self.highlighted_word = -1
        self.scale_factor = 1.0
        
        # Set background color
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(240, 240, 240))  # Light gray
        self.setPalette(palette)
        
        # Set size policy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(400, 600)
    
    def set_page(self, page_image, word_boxes):
        """Set the page image and word boxes
        
        Args:
            page_image: QImage of the page
            word_boxes: List of word bounding boxes
        """
        self.page_image = page_image
        self.word_boxes = word_boxes
        self.highlighted_word = -1
        
        # Update widget size to match page image
        if self.page_image:
            self.setMinimumSize(self.page_image.width(), self.page_image.height())
            self.resize(self.page_image.width(), self.page_image.height())
        
        self.update()
    
    def highlight_word(self, word_index):
        """Highlight a specific word
        
        Args:
            word_index: Index of the word to highlight
        """
        if self.word_boxes and 0 <= word_index < len(self.word_boxes):
            self.highlighted_word = word_index
            self.update()
    
    def clear_highlight(self):
        """Clear word highlighting"""
        self.highlighted_word = -1
        self.update()
    
    def ensure_visible(self, word_box):
        """Ensure a word box is visible in the scroll area
        
        Args:
            word_box: Bounding box of the word (x, y, width, height)
        """
        if isinstance(self.parent(), QScrollArea) and len(word_box) >= 4:
            try:
                scroll_area = self.parent()
                x, y, width, height = word_box
                
                # Convert to widget coordinates
                rect = QRectF(float(x), float(y), float(width), float(height))
                
                # Ensure visible with some padding
                padding = 50
                scroll_area.ensureVisible(
                    rect.center().x(),
                    rect.center().y(),
                    rect.width() + padding,
                    rect.height() + padding
                )
            except Exception as e:
                print(f"Error ensuring word visibility: {e}")
    
    def paintEvent(self, event):
        """Handle paint event
        
        Args:
            event: Paint event
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background
        painter.fillRect(self.rect(), QColor(240, 240, 240))
        
        # Draw page image
        if self.page_image:
            painter.drawImage(0, 0, self.page_image)
        
        # Draw highlighted word
        if (self.word_boxes and self.highlighted_word >= 0 and 
            self.highlighted_word < len(self.word_boxes)):
            try:
                word_box = self.word_boxes[self.highlighted_word]
                if len(word_box) >= 4:
                    x, y, width, height = word_box
                    
                    # Draw highlight rectangle with rounded corners
                    highlight_rect = QRectF(float(x), float(y), float(width), float(height))
                    painter.setPen(QPen(QColor(255, 165, 0), 2))  # Orange border
                    painter.setBrush(QBrush(QColor(255, 165, 0, 100)))  # Semi-transparent orange
                    painter.drawRoundedRect(highlight_rect, 2, 2)
            except Exception as e:
                print(f"Error drawing highlight: {e}")
    
    def sizeHint(self):
        """Return preferred size"""
        if self.page_image:
            return QSize(self.page_image.width(), self.page_image.height())
        return QSize(400, 600)