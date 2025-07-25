#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF View Widget with Word Highlighting for SpokenSense

This module implements a PDF viewer with word-level highlighting
for synchronization with TTS playback.
"""

import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QScrollArea, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QTimer
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QPixmap


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
        self.total_pages = self.pdf_reader.get_page_count()
        self.current_word_index = -1
        self.page_text = None
        self.word_boxes = None
        
        # Set up UI
        self._setup_ui()
        
        # Connect TTS callbacks
        self.tts_engine.set_word_callback(self._highlight_word)
    
    def _setup_ui(self):
        """Set up the widget UI"""
        # Main widget and layout
        self.content_widget = QWidget()
        self.setWidget(self.content_widget)
        self.setWidgetResizable(True)
        
        main_layout = QVBoxLayout(self.content_widget)
        
        # Page navigation
        nav_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("Previous")
        self.prev_button.clicked.connect(self._prev_page)
        
        self.page_label = QLabel(f"Page {self.current_page + 1} of {self.total_pages}")
        self.page_label.setAlignment(Qt.AlignCenter)
        
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self._next_page)
        
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.page_label)
        nav_layout.addWidget(self.next_button)
        
        main_layout.addLayout(nav_layout)
        
        # PDF display
        self.pdf_display = PDFPageWidget(self)
        main_layout.addWidget(self.pdf_display)
    
    def load_page(self, page_num):
        """Load a specific page
        
        Args:
            page_num: Page number to load (0-indexed)
        """
        if page_num < 0 or page_num >= self.total_pages:
            return
        
        # Stop TTS if playing
        self.stop_tts()
        
        # Update current page
        self.current_page = page_num
        self.page_label.setText(f"Page {self.current_page + 1} of {self.total_pages}")
        
        # Get page text and word boxes
        self.page_text, self.word_boxes = self.pdf_reader.get_page_text_and_boxes(page_num)
        
        # Update display
        page_image = self.pdf_reader.get_page_image(page_num)
        self.pdf_display.set_page(page_image, self.word_boxes)
        
        # Reset word highlighting
        self.current_word_index = -1
    
    def _prev_page(self):
        """Go to the previous page"""
        if self.current_page > 0:
            self.load_page(self.current_page - 1)
    
    def _next_page(self):
        """Go to the next page"""
        if self.current_page < self.total_pages - 1:
            self.load_page(self.current_page + 1)
    
    def play_tts(self):
        """Play TTS for the current page"""
        if self.page_text:
            self.tts_engine.speak(self.page_text, self.word_boxes)
    
    def pause_tts(self):
        """Pause TTS playback"""
        self.tts_engine.pause()
    
    def stop_tts(self):
        """Stop TTS playback"""
        self.tts_engine.stop()
        self.current_word_index = -1
        self.pdf_display.clear_highlight()
    
    def _highlight_word(self, word_index):
        """Highlight a word during TTS playback
        
        Args:
            word_index: Index of the word to highlight
        """
        if word_index < 0 or word_index >= len(self.word_boxes):
            return
        
        self.current_word_index = word_index
        self.pdf_display.highlight_word(word_index)
        
        # Ensure the highlighted word is visible
        word_box = self.word_boxes[word_index]
        self.pdf_display.ensure_visible(word_box)


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
        
        # Set background color
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(palette)
        
        # Set minimum size
        self.setMinimumSize(600, 800)
    
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
            word_box: Bounding box of the word
        """
        if isinstance(self.parent(), QScrollArea):
            scroll_area = self.parent()
            x, y, width, height = word_box
            
            # Convert to widget coordinates
            rect = QRectF(x, y, width, height)
            
            # Ensure visible with some padding
            padding = 50
            scroll_area.ensureVisible(
                rect.center().x(),
                rect.center().y(),
                rect.width() + padding,
                rect.height() + padding
            )
    
    def paintEvent(self, event):
        """Handle paint event
        
        Args:
            event: Paint event
        """
        painter = QPainter(self)
        
        # Draw page image
        if self.page_image:
            painter.drawImage(0, 0, self.page_image)
        
        # Draw highlighted word
        if self.word_boxes and self.highlighted_word >= 0:
            if self.highlighted_word < len(self.word_boxes):
                x, y, width, height = self.word_boxes[self.highlighted_word]
                
                # Draw highlight rectangle
                painter.setPen(QPen(QColor(255, 255, 0, 100), 1))
                painter.setBrush(QBrush(QColor(255, 255, 0, 100)))
                painter.drawRect(QRectF(x, y, width, height))