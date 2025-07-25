#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF Reader for SpokenSense

This module provides functionality for reading PDF files, extracting text with
word-level bounding boxes, and rendering pages as images.
"""

import os
import hashlib
import json
from PyQt5.QtGui import QImage, QPainter
import fitz  # PyMuPDF

from .extractor import PDFExtractor


class PDFReader:
    """PDF reader with text extraction and rendering capabilities"""
    
    def __init__(self, file_path, config):
        """Initialize the PDF reader
        
        Args:
            file_path: Path to the PDF file
            config: Application configuration
        """
        self.file_path = file_path
        self.config = config
        
        # Open the PDF document
        self.document = fitz.open(file_path)
        
        # Create extractor
        self.extractor = PDFExtractor(config)
        
        # Create cache directory if it doesn't exist
        self.cache_dir = os.path.join(config.get('data_dir'), 'cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Generate file hash for caching
        self.file_hash = self._get_file_hash()
    
    def _get_file_hash(self):
        """Generate MD5 hash of the PDF file for caching
        
        Returns:
            str: MD5 hash of the file
        """
        hasher = hashlib.md5()
        with open(self.file_path, 'rb') as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def get_page_count(self):
        """Get the number of pages in the PDF
        
        Returns:
            int: Number of pages
        """
        return len(self.document)
    
    def get_page_text_and_boxes(self, page_num):
        """Get text and word bounding boxes for a page
        
        Args:
            page_num: Page number (0-indexed)
        
        Returns:
            tuple: (page_text, word_boxes)
                page_text: Full text of the page
                word_boxes: List of word bounding boxes (x, y, width, height)
        """
        # Check cache first
        cache_file = os.path.join(
            self.cache_dir,
            f"{self.file_hash}_page_{page_num}_text.json"
        )
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                return cache_data['text'], cache_data['word_boxes']
            except (json.JSONDecodeError, KeyError):
                # Cache file is invalid, regenerate
                pass
        
        # Extract text and word boxes
        page = self.document[page_num]
        page_text, word_boxes = self.extractor.extract_text_and_boxes(page)
        
        # Cache the results
        cache_data = {
            'text': page_text,
            'word_boxes': word_boxes
        }
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
        except IOError as e:
            print(f"Error caching page text: {e}")
        
        return page_text, word_boxes
    
    def get_page_image(self, page_num, scale=1.0):
        """Render a page as an image
        
        Args:
            page_num: Page number (0-indexed)
            scale: Scale factor for rendering (default: 1.0)
        
        Returns:
            QImage: Rendered page image
        """
        # Check cache first
        cache_file = os.path.join(
            self.cache_dir,
            f"{self.file_hash}_page_{page_num}_image_{int(scale*100)}.png"
        )
        
        if os.path.exists(cache_file):
            image = QImage(cache_file)
            if not image.isNull():
                return image
        
        # Render the page
        page = self.document[page_num]
        
        # Get the page dimensions
        rect = page.rect
        
        # Calculate the target size
        width = int(rect.width * scale)
        height = int(rect.height * scale)
        
        # Render the page to a pixmap
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # Convert to QImage
        image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        
        # Cache the image
        try:
            image.save(cache_file)
        except IOError as e:
            print(f"Error caching page image: {e}")
        
        return image
    
    def close(self):
        """Close the PDF document"""
        if hasattr(self, 'document'):
            self.document.close()