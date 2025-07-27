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
import os
from typing import Tuple, List, Optional

class PDFExtractor:
    """PDF text extractor with word-level bounding boxes"""
    def __init__(self, config):
        """Initialize the PDF extractor
        Args:
            config: Application configuration
        """
        self.config = config or {}
        self.chunk_size = self.config.get('pdf_chunk_size', 300)
        self.chunk_overlap = self.config.get('pdf_chunk_overlap', 50)

    def extract_text_and_boxes(self, page) -> Tuple[str, List[Tuple[float, float, float, float]]]:
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
            print(f"PyMuPDF extraction failed, falling back to pdfplumber: {e}")
            try:
                # Fall back to pdfplumber
                return self._extract_with_pdfplumber(page)
            except Exception as e2:
                print(f"pdfplumber extraction also failed: {e2}")
                # Return empty results as last resort
                return "", []

    def _extract_with_pymupdf(self, page) -> Tuple[str, List[Tuple[float, float, float, float]]]:
        """Extract text and word boxes using PyMuPDF
        Args:
            page: PyMuPDF page object
        Returns:
            tuple: (page_text, word_boxes)
        """
        try:
            # Extract words with their bounding boxes using PyMuPDF's word extraction
            words = page.get_text("words")
            if not words:
                return "", []
            # Sort words by reading order (top to bottom, left to right)
            words.sort(key=lambda w: (w[1], w[0]))  # Sort by y0, then x0
            # Group words into lines based on vertical proximity
            lines = self._group_words_into_lines(words)
            # Process lines to create text and bounding boxes
            page_text_lines = []
            word_boxes = []
            for line_words in lines:
                # Create line text
                line_text = " ".join([word[4] for word in line_words])
                page_text_lines.append(line_text)
                # Add individual word boxes
                for word in line_words:
                    x0, y0, x1, y1 = word[0], word[1], word[2], word[3]
                    word_boxes.append((float(x0), float(y0), float(x1 - x0), float(y1 - y0)))
            # Join lines with newlines
            page_text = "\n".join(page_text_lines)
            return page_text, word_boxes
        except Exception as e:
            print(f"Error in PyMuPDF extraction: {e}")
            raise

    def _group_words_into_lines(self, words, line_threshold=5.0) -> List[List]:
        """Group words into lines based on vertical proximity
        Args:
            words: List of word tuples from PyMuPDF
            line_threshold: Vertical distance threshold for line grouping
        Returns:
            List of lines, where each line is a list of words
        """
        if not words:
            return []
        lines = []
        current_line = [words[0]]
        current_line_y = (words[0][1] + words[0][3]) / 2  # Average of y0 and y1
        for word in words[1:]:
            word_y = (word[1] + word[3]) / 2  # Average of y0 and y1
            # Check if word is on the same line (within threshold)
            if abs(word_y - current_line_y) <= line_threshold:
                current_line.append(word)
            else:
                # Sort current line by x-coordinate and add to lines
                current_line.sort(key=lambda w: w[0])  # Sort by x0
                lines.append(current_line)
                # Start new line
                current_line = [word]
                current_line_y = word_y
        # Don't forget the last line
        if current_line:
            current_line.sort(key=lambda w: w[0])  # Sort by x0
            lines.append(current_line)
        return lines

    def _extract_with_pdfplumber(self, page) -> Tuple[str, List[Tuple[float, float, float, float]]]:
        """Extract text and word boxes using pdfplumber (fallback)
        Args:
            page: PyMuPDF page object (used to get page number and file path)
        Returns:
            tuple: (page_text, word_boxes)
        """
        # Note: This method is complex and relies on re-opening the PDF with pdfplumber.
        # Ensure pdf_path is correctly obtained from the PyMuPDF page object.
        # This can sometimes be fragile depending on how the document was opened.
        try:
            # Get page number and file path from PyMuPDF page
            page_num = page.number
            # Accessing the parent document's name might not always work as expected.
            # It depends on how the document was loaded. Let's assume the caller
            # (PDFReader) passes the path correctly and handles this.
            # For fallback, we might need the path passed in or stored differently.
            # Let's assume the parent document object has the name attribute.
            pdf_document = page.parent
            if hasattr(pdf_document, 'name'):
                 pdf_path = pdf_document.name
            else:
                 # Fallback or error handling needed if name is not available
                 raise AttributeError("Cannot determine PDF file path from PyMuPDF page object for pdfplumber fallback.")

            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found for pdfplumber: {pdf_path}")
            with pdfplumber.open(pdf_path) as pdf:
                if page_num >= len(pdf.pages):
                    raise IndexError(f"Page {page_num} not found in PDF for pdfplumber")
                plumber_page = pdf.pages[page_num]
                # Extract words with their bounding boxes
                words = plumber_page.extract_words()
                if not words:
                    return "", []
                # Sort words by reading order
                words.sort(key=lambda w: (w['top'], w['x0']))
                # Group words into lines
                lines = self._group_plumber_words_into_lines(words)
                # Process lines to create text and bounding boxes
                page_text_lines = []
                word_boxes = []
                for line_words in lines:
                    # Create line text
                    line_text = " ".join([word['text'] for word in line_words])
                    page_text_lines.append(line_text)
                    # Add individual word boxes
                    for word in line_words:
                        x0, top, x1, bottom = word['x0'], word['top'], word['x1'], word['bottom']
                        word_boxes.append((float(x0), float(top), float(x1 - x0), float(bottom - top)))
                # Join lines with newlines
                page_text = "\n".join(page_text_lines)
                return page_text, word_boxes
        except Exception as e:
            print(f"Error in pdfplumber extraction: {e}")
            raise

    def _group_plumber_words_into_lines(self, words, line_threshold=5.0) -> List[List]:
        """Group pdfplumber words into lines based on vertical proximity
        Args:
            words: List of word dictionaries from pdfplumber
            line_threshold: Vertical distance threshold for line grouping
        Returns:
            List of lines, where each line is a list of words
        """
        if not words:
            return []
        lines = []
        current_line = [words[0]]
        current_line_y = words[0]['top']
        for word in words[1:]:
            word_y = word['top']
            # Check if word is on the same line (within threshold)
            if abs(word_y - current_line_y) <= line_threshold:
                current_line.append(word)
            else:
                # Sort current line by x-coordinate and add to lines
                current_line.sort(key=lambda w: w['x0'])
                lines.append(current_line)
                # Start new line
                current_line = [word]
                current_line_y = word_y
        # Don't forget the last line
        if current_line:
            current_line.sort(key=lambda w: w['x0'])
            lines.append(current_line)
        return lines

    def chunk_text(self, text: str, chunk_size: Optional[int] = None, overlap: Optional[int] = None) -> List[dict]: # Changed return type hint
        """Split text into chunks for AI processing
        Args:
            text: Text to chunk
            chunk_size: Target chunk size in words (default: from config)
            overlap: Overlap between chunks in words (default: from config)
        Returns:
            list: List of chunk dictionaries with metadata
        """
        if not text:
            return []
        chunk_size = chunk_size or self.chunk_size
        overlap = overlap or self.chunk_overlap
        # Split text into words while preserving some punctuation
        words = re.findall(r'\S+', text)
        if not words:
            return []
        chunks = []
        chunk_id = 0
        # Create overlapping chunks
        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            if not chunk_words:
                break
            chunk_text = " ".join(chunk_words)
            # Create chunk with metadata
            chunk = {
                'text': chunk_text,
                'start_word': i,
                'end_word': min(i + chunk_size, len(words)),
                'chunk_id': chunk_id
            }
            chunks.append(chunk)
            chunk_id += 1
            # Break if we've covered all words
            if i + chunk_size >= len(words):
                break
        return chunks

    def get_document_chunks(self, pdf_document, max_pages: Optional[int] = None) -> List[dict]:
        """Extract chunks from entire document
        Args:
            pdf_document: PyMuPDF document object
            max_pages: Maximum number of pages to process (None for all)
        Returns:
            list: List of chunk dictionaries with page information
        """
        try:
            chunks = []
            page_count = len(pdf_document)

            # --- FIX: Robust handling of max_pages ---
            pages_to_process = page_count
            if max_pages is not None:
                try:
                    pages_to_process = min(int(max_pages), page_count)
                except (ValueError, TypeError):
                    print(f"Warning: Invalid max_pages value '{max_pages}', processing all pages.")

            for page_num in range(pages_to_process):
                page = pdf_document[page_num]
                # Extract text from page
                page_text, _ = self.extract_text_and_boxes(page)
                if page_text.strip():
                    # Chunk the page text
                    page_chunks = self.chunk_text(page_text)
                    # Add page information to chunks
                    for chunk in page_chunks:
                        chunk_with_page = {
                            'text': chunk['text'],
                            'page': page_num,
                            'start_word': chunk['start_word'],
                            'end_word': chunk['end_word'],
                            'chunk_id': chunk['chunk_id']
                        }
                        chunks.append(chunk_with_page)
            return chunks
        except Exception as e:
            print(f"Error getting document chunks: {e}")
            return []

    def clean_text(self, text: str, options: dict = None) -> str: # ONLY ONE DEFINITION NOW
        """Clean extracted text based on options
        Args:
            text: Text to clean
            options: Cleaning options dictionary
        Returns:
            str: Cleaned text
        """
        if not text:
            return text
        # Default options if none provided
        default_options = {
            'remove_extra_whitespace': True,
            'remove_hyphens': True,
            'fix_ocr_issues': True
        }
        if options:
            default_options.update(options)
        options = default_options

        # Remove extra whitespace
        if options.get('remove_extra_whitespace', True):
            text = re.sub(r'\s+', ' ', text).strip()
        # Remove hyphens at line breaks
        if options.get('remove_hyphens', True):
            # Corrected regex to handle line breaks properly
            text = re.sub(r'-\s*\n\s*', '', text)
        # Fix common OCR issues
        if options.get('fix_ocr_issues', True):
            # Replace common OCR artifacts
            text = re.sub(r'\s*-\s*', '-', text)  # Fix hyphens
            text = re.sub(r'\s*\.\s*\.\s*\.', '...', text)  # Fix ellipses
        return text
