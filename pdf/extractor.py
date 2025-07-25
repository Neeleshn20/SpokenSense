#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF Extractor for SpokenSense

This module provides functionality for extracting text and word-level bounding boxes
from PDF documents using PyMuPDF (primary) and pdfplumber (fallback).
"""

import fitz  # PyMuPDF
import pdfplumber
import re


class PDFExtractor:
    """PDF text extractor with word-level bounding boxes"""
    
    def __init__(self, config):
        """Initialize the PDF extractor
        
        Args:
            config: Application configuration
        """
        self.config = config
    
    def extract_text_and_boxes(self, page):
        """Extract text and word bounding boxes from a page
        
        Args:
            page: PyMuPDF page object
        
        Returns:
            tuple: (page_text, word_boxes)
                page_text: Full text of the page
                word_boxes: List of word bounding boxes (x, y, width, height)
        """
        try:
            # Try PyMuPDF first (faster and more accurate)
            return self._extract_with_pymupdf(page)
        except Exception as e:
            print(f"PyMuPDF extraction failed: {e}")
            # Fall back to pdfplumber
            return self._extract_with_pdfplumber(page)
    
    def _extract_with_pymupdf(self, page):
        """Extract text and word boxes using PyMuPDF
        
        Args:
            page: PyMuPDF page object
        
        Returns:
            tuple: (page_text, word_boxes)
        """
        # Extract words with their bounding boxes
        words = page.get_text("words")
        
        # Sort words by vertical position (top to bottom, then left to right)
        words.sort(key=lambda w: (w[3], w[0]))  # Sort by y1, then x0
        
        # Process words to create text and bounding boxes
        page_text = ""
        word_boxes = []
        
        current_line_y = -1
        line_words = []
        
        for word in words:
            x0, y0, x1, y1, text, block_no, line_no, word_no = word
            
            # Check if we're on a new line
            if current_line_y == -1 or abs(y0 - current_line_y) > 5:  # Threshold for new line
                # Process previous line if it exists
                if line_words:
                    line_text = " ".join([w[4] for w in line_words])
                    page_text += line_text + "\n"
                    
                    # Add word boxes for the line
                    for w in line_words:
                        word_boxes.append((w[0], w[1], w[2] - w[0], w[3] - w[1]))
                
                # Start new line
                current_line_y = y0
                line_words = [word]
            else:
                # Continue current line
                line_words.append(word)
        
        # Process the last line
        if line_words:
            line_text = " ".join([w[4] for w in line_words])
            page_text += line_text
            
            # Add word boxes for the line
            for w in line_words:
                word_boxes.append((w[0], w[1], w[2] - w[0], w[3] - w[1]))
        
        return page_text, word_boxes
    
    def _extract_with_pdfplumber(self, page):
        """Extract text and word boxes using pdfplumber (fallback)
        
        Args:
            page: PyMuPDF page object
        
        Returns:
            tuple: (page_text, word_boxes)
        """
        # Convert PyMuPDF page to pdfplumber page
        # This is a bit hacky, but we need to get the page number and open with pdfplumber
        page_num = page.number
        pdf_path = page.parent.name
        
        with pdfplumber.open(pdf_path) as pdf:
            plumber_page = pdf.pages[page_num]
            
            # Extract words with their bounding boxes
            words = plumber_page.extract_words()
            
            # Process words to create text and bounding boxes
            page_text = ""
            word_boxes = []
            
            current_line_y = -1
            line_words = []
            
            for word in words:
                x0, top, x1, bottom = (
                    word['x0'],
                    word['top'],
                    word['x1'],
                    word['bottom']
                )
                text = word['text']
                
                # Check if we're on a new line
                if current_line_y == -1 or abs(top - current_line_y) > 5:  # Threshold for new line
                    # Process previous line if it exists
                    if line_words:
                        line_text = " ".join([w['text'] for w in line_words])
                        page_text += line_text + "\n"
                        
                        # Add word boxes for the line
                        for w in line_words:
                            word_boxes.append((
                                w['x0'],
                                w['top'],
                                w['x1'] - w['x0'],
                                w['bottom'] - w['top']
                            ))
                    
                    # Start new line
                    current_line_y = top
                    line_words = [word]
                else:
                    # Continue current line
                    line_words.append(word)
            
            # Process the last line
            if line_words:
                line_text = " ".join([w['text'] for w in line_words])
                page_text += line_text
                
                # Add word boxes for the line
                for w in line_words:
                    word_boxes.append((
                        w['x0'],
                        w['top'],
                        w['x1'] - w['x0'],
                        w['bottom'] - w['top']
                    ))
        
        return page_text, word_boxes
    
    def chunk_text(self, text, chunk_size=300, overlap=50):
        """Split text into chunks for AI processing
        
        Args:
            text: Text to chunk
            chunk_size: Target chunk size in words (default: 300)
            overlap: Overlap between chunks in words (default: 50)
        
        Returns:
            list: List of text chunks
        """
        # Split text into words
        words = re.findall(r'\b\w+\b', text)
        
        # Create chunks
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)
        
        return chunks