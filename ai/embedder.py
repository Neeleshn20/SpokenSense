#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Text Embedder for SpokenSense

This module provides functionality for generating text embeddings
using sentence-transformers models.
"""

import os
import numpy as np
from sentence_transformers import SentenceTransformer


class TextEmbedder:
    """Text embedder using sentence-transformers"""
    
    def __init__(self, config):
        """Initialize the text embedder
        
        Args:
            config: Application configuration
        """
        self.config = config or {}
        self.model = None
        
        # Initialize embedder
        self._initialize_embedder()
    
    def _initialize_embedder(self):
        """Initialize the embedding model"""
        try:
            # Get model name from config
            model_name = self.config.get('embedding_model', 'all-MiniLM-L6-v2')
            
            # Set cache directory
            cache_dir = self.config.get('model_cache_dir', './models_cache')
            os.makedirs(cache_dir, exist_ok=True)
            
            # Initialize model with cache
            self.model = SentenceTransformer(model_name, cache_folder=cache_dir)
            
        except Exception as e:
            print(f"Error initializing embedder: {e}")
            self.model = None
    
    def embed_text(self, text):
        """Generate embeddings for text
        
        Args:
            text: Text to embed
        
        Returns:
            numpy.ndarray: Text embedding
        """
        if not self.model:
            print("Embedder not initialized")
            return None
        
        if not text or not isinstance(text, str):
            print("Invalid text input")
            return None
            
        try:
            # Generate embedding
            embedding = self.model.encode(text)
            return embedding
        except Exception as e:
            print(f"Error embedding text: {e}")
            return None
    
    def embed_texts(self, texts, batch_size=32):
        """Generate embeddings for multiple texts with batching
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
        
        Returns:
            list: List of text embeddings
        """
        if not self.model:
            print("Embedder not initialized")
            return None
            
        if not texts or not isinstance(texts, (list, tuple)):
            print("Invalid texts input")
            return None
        
        try:
            # Generate embeddings with batching
            embeddings = self.model.encode(texts, batch_size=batch_size)
            return embeddings
        except Exception as e:
            print(f"Error embedding texts: {e}")
            return None
    
    def similarity(self, embedding1, embedding2):
        """Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
        
        Returns:
            float: Cosine similarity
        """
        if embedding1 is None or embedding2 is None:
            print("Cannot compute similarity with None embeddings")
            return 0.0
            
        try:
            # Normalize embeddings
            embedding1_norm = embedding1 / np.linalg.norm(embedding1)
            embedding2_norm = embedding2 / np.linalg.norm(embedding2)
            
            # Calculate cosine similarity
            similarity = np.dot(embedding1_norm, embedding2_norm)
            return float(similarity)
        except Exception as e:
            print(f"Error computing similarity: {e}")
            return 0.0
    
    def get_model_info(self):
        """Get information about the loaded model"""
        if not self.model:
            return "No model loaded"
        
        try:
            return {
                'model_name': self.model._modules['0'].auto_model.config._name_or_path,
                'max_seq_length': getattr(self.model, 'max_seq_length', 'Unknown'),
                'device': str(next(self.model.parameters()).device)
            }
        except Exception as e:
            return f"Error getting model info: {e}"
    
    def is_available(self):
        """Check if the embedder is properly initialized"""
        return self.model is not None