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
import logging
from typing import Tuple, List, Optional, Union
from PyQt5.QtGui import QImage, QPainter, QPixmap
from PyQt5.QtCore import Qt
import fitz  # PyMuPDF

from pdf.extractor import PDFExtractor  # Fixed import path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFReader:
    """PDF reader with text extraction and rendering capabilities"""
    
    def __init__(self, file_path: str, config: dict):
        """Initialize the PDF reader
        
        Args:
            file_path: Path to the PDF file
            config: Application configuration
        """
        self.file_path = file_path
        self.config = config or {}
        
        # Validate file path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        # Open the PDF document
        try:
            self.document = fitz.open(file_path)
            logger.info(f"Successfully opened PDF: {file_path}")
        except Exception as e:
            logger.error(f"Error opening PDF {file_path}: {e}")
            raise
        
        # Create extractor
        self.extractor = PDFExtractor(config)
        
        # Set up cache directory
        self.cache_dir = os.path.join(self.config.get('data_dir', './data'), 'cache')
        self._ensure_cache_directory()
        
        # Generate file hash for caching
        self.file_hash = self._get_file_hash()
        
        # Page cache for performance
        self._page_cache = {}  # In-memory cache for recently accessed pages
        self._max_cache_size = config.get('max_page_cache_size', 10)
        self._page_cache = {}  # In-memory cache for rendered pages
    
    def _manage_cache_size(self):
        """Manage in-memory cache size"""
        if len(self._page_cache) > self._max_cache_size:
            # Remove oldest entries
            keys_to_remove = list(self._page_cache.keys())[:2]
            for key in keys_to_remove:
                del self._page_cache[key]

    def preload_pages(self, page_numbers: List[int], scale: float = 1.5):
        """Preload pages into cache for faster access
        
        Args:
            page_numbers: List of page numbers to preload
            scale: Scale factor for images
        """
        for page_num in page_numbers:
            if 0 <= page_num < self.get_page_count():
                try:
                    self.get_page_text_and_boxes(page_num)
                    self.get_page_image(page_num, scale)
                    logger.debug(f"Preloaded page {page_num}")
                except Exception as e:
                    logger.warning(f"Failed to preload page {page_num}: {e}")

    def _ensure_cache_directory(self):
        """Ensure cache directory exists"""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            logger.info(f"Cache directory ready: {self.cache_dir}")
        except Exception as e:
            logger.error(f"Error creating cache directory {self.cache_dir}: {e}")
            raise
    
    def _get_file_hash(self) -> str:
        """Generate MD5 hash of the PDF file for caching
        
        Returns:
            str: MD5 hash of the file
        """
        try:
            hasher = hashlib.md5()
            with open(self.file_path, 'rb') as f:
                # Read in chunks to handle large files efficiently
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            file_hash = hasher.hexdigest()
            logger.debug(f"Generated file hash for {self.file_path}: {file_hash}")
            return file_hash
        except Exception as e:
            logger.error(f"Error generating file hash: {e}")
            # Fallback to filename-based hash
            return hashlib.md5(self.file_path.encode()).hexdigest()
    
    def get_page_count(self) -> int:
        """Get the number of pages in the PDF
        
        Returns:
            int: Number of pages
        """
        if not hasattr(self, 'document'):
            return 0
        return len(self.document)
    
    def get_page_text_and_boxes(self, page_num: int) -> Tuple[str, List[Tuple[float, float, float, float]]]:
        """Get text and word bounding boxes for a page
        
        Args:
            page_num: Page number (0-indexed)
        
        Returns:
            tuple: (page_text, word_boxes)
                page_text: Full text of the page
                word_boxes: List of word bounding boxes (x, y, width, height)
        """
        # Validate page number
        if not hasattr(self, 'document'):
            raise RuntimeError("PDF document not loaded")
        
        if page_num < 0 or page_num >= self.get_page_count():
            raise IndexError(f"Page number {page_num} out of range (0-{self.get_page_count()-1})")
        
        # Check in-memory cache first
        cache_key = f"text_{page_num}"
        if cache_key in self._page_cache:
            logger.debug(f"Retrieved page {page_num} text from memory cache")
            return self._page_cache[cache_key]
        
        # Check file cache
        cache_file = os.path.join(
            self.cache_dir,
            f"{self.file_hash}_page_{page_num}_text.json"
        )
        
        if os.path.exists(cache_file) and self.config.get('pdf_cache_enabled', True):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                result = (cache_data['text'], cache_data['word_boxes'])
                
                # Store in memory cache
                self._page_cache[cache_key] = result
                logger.debug(f"Retrieved page {page_num} text from file cache")
                return result
            except (json.JSONDecodeError, KeyError, IOError) as e:
                logger.warning(f"Cache file invalid for page {page_num}, regenerating: {e}")
            except Exception as e:
                logger.error(f"Error reading cache for page {page_num}: {e}")
        
        # Extract text and word boxes
        try:
            page = self.document[page_num]
            page_text, word_boxes = self.extractor.extract_text_and_boxes(page)
            
            # Cache the results
            cache_data = {
                'text': page_text,
                'word_boxes': word_boxes,
                'timestamp': str(fitz.TOOLS.get_time())
            }
            
            if self.config.get('pdf_cache_enabled', True):
                try:
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(cache_data, f, ensure_ascii=False, indent=2)
                    logger.debug(f"Cached page {page_num} text to {cache_file}")
                except IOError as e:
                    logger.warning(f"Error caching page text: {e}")
            
            # Store in memory cache
            self._page_cache[cache_key] = (page_text, word_boxes)
            
            return page_text, word_boxes
            
        except Exception as e:
            logger.error(f"Error extracting text from page {page_num}: {e}")
            return "", []
    
    def get_page_image(self, page_num: int, scale: float = 1.5) -> QImage:
        """Render a page as an image
        
        Args:
            page_num: Page number (0-indexed)
            scale: Scale factor for rendering (default: 1.5 for better quality)
        
        Returns:
            QImage: Rendered page image
        """
        # Validate page number
        if not hasattr(self, 'document'):
            raise RuntimeError("PDF document not loaded")
        
        if page_num < 0 or page_num >= self.get_page_count():
            raise IndexError(f"Page number {page_num} out of range (0-{self.get_page_count()-1})")
        
        # Check in-memory cache first
        cache_key = f"image_{page_num}_{scale}"
        if cache_key in self._page_cache:
            logger.debug(f"Retrieved page {page_num} image from memory cache")
            return self._page_cache[cache_key]
        
        # Check file cache
        cache_file = os.path.join(
            self.cache_dir,
            f"{self.file_hash}_page_{page_num}_image_{int(scale*100)}.png"
        )
        
        if os.path.exists(cache_file) and self.config.get('pdf_cache_enabled', True):
            image = QImage(cache_file)
            if not image.isNull():
                # Store in memory cache
                self._page_cache[cache_key] = image
                logger.debug(f"Retrieved page {page_num} image from file cache")
                return image
            else:
                logger.warning(f"Cache image file invalid: {cache_file}")
        
        # Render the page
        try:
            page = self.document[page_num]
            
            # Get the page dimensions
            rect = page.rect
            
            # Calculate the target size with better quality
            width = int(rect.width * scale)
            height = int(rect.height * scale)
            
            # Render the page to a pixmap with anti-aliasing
            mat = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat, alpha=False, annots=True)
            
            # Convert to QImage
            image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            
            # Apply basic image enhancement
            if image.isNull():
                logger.warning(f"Generated null image for page {page_num}")
                return QImage()  # Return empty image
            
            # Cache the image
            if self.config.get('pdf_cache_enabled', True):
                try:
                    success = image.save(cache_file, "PNG", 95)  # High quality
                    if success:
                        logger.debug(f"Cached page {page_num} image to {cache_file}")
                    else:
                        logger.warning(f"Failed to save image cache: {cache_file}")
                except IOError as e:
                    logger.warning(f"Error caching page image: {e}")
            
            # Store in memory cache
            self._page_cache[cache_key] = image
            
            return image
            
        except Exception as e:
            logger.error(f"Error rendering page {page_num} as image: {e}")
            return QImage()  # Return empty image on error
    
    def get_document_chunks(self, max_pages: Optional[int] = None) -> List[dict]:
        """Get document chunks for AI processing
        
        Args:
            max_pages: Maximum number of pages to process (None for all)
        
        Returns:
            list: List of chunk dictionaries with page information
        """
        try:
            if not hasattr(self, 'extractor'):
                raise RuntimeError("PDF extractor not initialized")
            
            chunks = self.extractor.get_document_chunks(self.document, max_pages)
            logger.info(f"Extracted {len(chunks)} chunks from document")
            return chunks
        except Exception as e:
            logger.error(f"Error getting document chunks: {e}")
            return []
    
    def get_page_metadata(self, page_num: int) -> dict:
        """Get metadata for a specific page
        
        Args:
            page_num: Page number (0-indexed)
        
        Returns:
            dict: Page metadata
        """
        try:
            if page_num < 0 or page_num >= self.get_page_count():
                return {}
            
            page = self.document[page_num]
            rect = page.rect
            
            return {
                'page_number': page_num,
                'width': rect.width,
                'height': rect.height,
                'rotation': page.rotation,
                'is_empty': len(page.get_text()) == 0
            }
        except Exception as e:
            logger.error(f"Error getting page metadata for page {page_num}: {e}")
            return {}
    
    def get_document_info(self) -> dict:
        """Get document information
        
        Returns:
            dict: Document information
        """
        try:
            info = self.document.metadata
            return {
                'title': info.get('title', ''),
                'author': info.get('author', ''),
                'subject': info.get('subject', ''),
                'creator': info.get('creator', ''),
                'producer': info.get('producer', ''),
                'creationDate': info.get('creationDate', ''),
                'modDate': info.get('modDate', ''),
                'page_count': self.get_page_count(),
                'file_path': self.file_path
            }
        except Exception as e:
            logger.error(f"Error getting document info: {e}")
            return {
                'page_count': self.get_page_count(),
                'file_path': self.file_path
            }
    
    def cleanup_cache(self, max_age_days: int = 30):
        """Clean up old cache files
        
        Args:
            max_age_days: Maximum age of cache files in days
        """
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_days * 24 * 60 * 60
            
            cleaned_files = 0
            for filename in os.listdir(self.cache_dir):
                if filename.startswith(self.file_hash):
                    file_path = os.path.join(self.cache_dir, filename)
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > max_age_seconds:
                        os.remove(file_path)
                        cleaned_files += 1
            
            if cleaned_files > 0:
                logger.info(f"Cleaned up {cleaned_files} old cache files")
                
        except Exception as e:
            logger.error(f"Error cleaning cache: {e}")
    
    def close(self):
        """Close the PDF document and cleanup resources"""
        try:
            # Clear memory cache
            self._page_cache.clear()
            
            # Close document
            if hasattr(self, 'document'):
                self.document.close()
                logger.info(f"Closed PDF document: {self.file_path}")
            
        except Exception as e:
            logger.error(f"Error closing PDF document: {e}")
    
    def cleanup(self):
        """Alias for close() for consistency"""
        self.close()
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.close()
        except:
            pass