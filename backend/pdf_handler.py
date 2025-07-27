import fitz  # PyMuPDF
import pdfplumber
import pickle
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import hashlib
import streamlit as st

class PDFHandler:
    """Handles PDF loading, text extraction, and processing with caching."""
    
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.current_pdf = None
        self.pdf_data = None
        
    def _get_cache_key(self, pdf_path: str) -> str:
        """Generate a cache key based on PDF file hash."""
        with open(pdf_path, 'rb') as f:
            pdf_hash = hashlib.md5(f.read()).hexdigest()
        return f"pdf_{pdf_hash}"
    
    def _load_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Load processed PDF data from cache."""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                st.warning(f"Cache loading failed: {e}")
                return None
        return None
    
    def _save_to_cache(self, cache_key: str, data: Dict) -> None:
        """Save processed PDF data to cache."""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            st.warning(f"Cache saving failed: {e}")
    
    def extract_text_pymupdf(self, pdf_path: str) -> List[Dict]:
        """Extract text using PyMuPDF with word-level positioning."""
        doc = fitz.open(pdf_path)
        pages_data = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Extract text with word positions
            words = page.get_text("words")  # Returns list of (x0, y0, x1, y1, "word", block_no, line_no, word_no)
            
            # Extract full text
            text = page.get_text()
            
            # Split into sentences for TTS
            sentences = self._split_into_sentences(text)
            
            page_data = {
                'page_num': page_num + 1,
                'text': text,
                'words': words,
                'sentences': sentences,
                'bbox': page.rect  # Page bounding box
            }
            pages_data.append(page_data)
        
        doc.close()
        return pages_data
    
    def extract_text_pdfplumber(self, pdf_path: str) -> List[Dict]:
        """Extract text using pdfplumber as fallback."""
        pages_data = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                
                # Get word positions if available
                words = []
                try:
                    words_data = page.extract_words()
                    for word_data in words_data:
                        words.append((
                            word_data['x0'], word_data['top'], 
                            word_data['x1'], word_data['bottom'], 
                            word_data['text'], 0, 0, 0
                        ))
                except:
                    pass
                
                sentences = self._split_into_sentences(text)
                
                page_data = {
                    'page_num': page_num + 1,
                    'text': text,
                    'words': words,
                    'sentences': sentences,
                    'bbox': page.bbox if hasattr(page, 'bbox') else (0, 0, 612, 792)
                }
                pages_data.append(page_data)
        
        return pages_data
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences for TTS processing."""
        import re
        # Simple sentence splitting - can be enhanced with NLTK if needed
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    
    def load_pdf(self, pdf_file) -> Dict:
        """Load and process PDF file with caching."""
        # Save uploaded file temporarily
        temp_path = self.cache_dir / "temp_upload.pdf"
        with open(temp_path, "wb") as f:
            f.write(pdf_file.read())
        
        # Generate cache key
        cache_key = self._get_cache_key(str(temp_path))
        
        # Try to load from cache first
        cached_data = self._load_from_cache(cache_key)
        if cached_data:
            st.success("📁 Loaded from cache!")
            self.pdf_data = cached_data
            return cached_data
        
        st.info("🔄 Processing PDF...")
        
        # Extract text using PyMuPDF first, fallback to pdfplumber
        try:
            pages_data = self.extract_text_pymupdf(str(temp_path))
            extraction_method = "PyMuPDF"
        except Exception as e:
            st.warning(f"PyMuPDF failed: {e}. Trying pdfplumber...")
            try:
                pages_data = self.extract_text_pdfplumber(str(temp_path))
                extraction_method = "pdfplumber"
            except Exception as e2:
                st.error(f"Both extraction methods failed: {e2}")
                return {}
        
        # Prepare final data structure
        pdf_data = {
            'filename': pdf_file.name,
            'pages': pages_data,
            'total_pages': len(pages_data),
            'extraction_method': extraction_method,
            'total_text': '\n'.join([page['text'] for page in pages_data])
        }
        
        # Save to cache
        self._save_to_cache(cache_key, pdf_data)
        
        # Clean up temp file
        os.remove(temp_path)
        
        self.pdf_data = pdf_data
        st.success(f"✅ PDF processed using {extraction_method}!")
        return pdf_data
    
    def get_page_text(self, page_num: int) -> str:
        """Get text for a specific page."""
        if self.pdf_data and 0 <= page_num < len(self.pdf_data['pages']):
            return self.pdf_data['pages'][page_num]['text']
        return ""
    
    def get_page_sentences(self, page_num: int) -> List[str]:
        """Get sentences for a specific page."""
        if self.pdf_data and 0 <= page_num < len(self.pdf_data['pages']):
            return self.pdf_data['pages'][page_num]['sentences']
        return []
    
    def get_all_text(self) -> str:
        """Get all text from the PDF."""
        if self.pdf_data:
            return self.pdf_data['total_text']
        return ""
    
    def search_text(self, query: str) -> List[Dict]:
        """Search for text across all pages."""
        results = []
        if not self.pdf_data:
            return results
        
        query_lower = query.lower()
        for page in self.pdf_data['pages']:
            text_lower = page['text'].lower()
            if query_lower in text_lower:
                # Find all occurrences
                start = 0
                while True:
                    pos = text_lower.find(query_lower, start)
                    if pos == -1:
                        break
                    
                    # Extract context around the match
                    context_start = max(0, pos - 50)
                    context_end = min(len(page['text']), pos + len(query) + 50)
                    context = page['text'][context_start:context_end]
                    
                    results.append({
                        'page_num': page['page_num'],
                        'position': pos,
                        'context': context,
                        'match': page['text'][pos:pos + len(query)]
                    })
                    start = pos + 1
        
        return results
