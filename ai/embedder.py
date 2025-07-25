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
        self.config = config
        self.model = None
        
        # Initialize embedder
        self._initialize_embedder()
    
    def _initialize_embedder(self):
        """Initialize the embedding model"""
        try:
            # Get model name from config
            model_name = self.config.get('embedding_model', 'all-MiniLM-L6-v2')
            
            # Initialize model
            self.model = SentenceTransformer(model_name)
            
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
        
        # Generate embedding
        embedding = self.model.encode(text)
        
        return embedding
    
    def embed_texts(self, texts):
        """Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
        
        Returns:
            list: List of text embeddings
        """
        if not self.model:
            print("Embedder not initialized")
            return None
        
        # Generate embeddings
        embeddings = self.model.encode(texts)
        
        return embeddings
    
    def similarity(self, embedding1, embedding2):
        """Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
        
        Returns:
            float: Cosine similarity
        """
        # Normalize embeddings
        embedding1 = embedding1 / np.linalg.norm(embedding1)
        embedding2 = embedding2 / np.linalg.norm(embedding2)
        
        # Calculate cosine similarity
        similarity = np.dot(embedding1, embedding2)
        
        return similarity