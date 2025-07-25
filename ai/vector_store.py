#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Vector Store for SpokenSense

This module provides functionality for storing and retrieving text embeddings
using ChromaDB as a persistent local vector database.
"""

import os
import hashlib
import chromadb
# Remove Settings import as it's deprecated


class VectorStore:
    """Vector store using ChromaDB"""
    
    def __init__(self, config, file_path=None):
        """Initialize the vector store
        
        Args:
            config: Application configuration
            file_path: Path to the PDF file (for collection naming)
        """
        self.config = config
        self.file_path = file_path
        self.client = None
        self.collection = None
        
        # Initialize vector store
        self._initialize_vector_store()
    
    def _initialize_vector_store(self):
        """Initialize the ChromaDB vector store"""
        try:
            # Get embeddings directory from config
            embeddings_dir = os.path.join(self.config.get('data_dir'), 'embeddings')
            os.makedirs(embeddings_dir, exist_ok=True)
            
            # Initialize ChromaDB client with updated configuration
            # Using the new client configuration format
            self.client = chromadb.PersistentClient(path=embeddings_dir)
            
            # Create or get collection for the file
            if self.file_path:
                collection_name = self._get_collection_name()
                self.collection = self.client.get_or_create_collection(collection_name)
            
        except Exception as e:
            print(f"Error initializing vector store: {e}")
            self.client = None
            self.collection = None
    
    def _get_collection_name(self):
        """Generate a collection name based on the file path
        
        Returns:
            str: Collection name
        """
        if not self.file_path:
            return "default_collection"
        
        # Generate MD5 hash of the file path
        hasher = hashlib.md5()
        hasher.update(self.file_path.encode('utf-8'))
        file_hash = hasher.hexdigest()
        
        # Use the hash as the collection name
        return f"pdf_{file_hash}"
    
    def add_texts(self, texts, metadatas=None, ids=None):
        """Add texts to the vector store
        
        Args:
            texts: List of texts to add
            metadatas: List of metadata dictionaries
            ids: List of document IDs
        
        Returns:
            list: List of document IDs
        """
        if not self.collection:
            print("Vector store not initialized")
            return None
        
        # Generate IDs if not provided
        if not ids:
            ids = [f"doc_{i}" for i in range(len(texts))]
        
        # Generate default metadata if not provided
        if not metadatas:
            metadatas = [{} for _ in range(len(texts))]
        
        # Add texts to collection
        self.collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        return ids
    
    def similarity_search(self, query, k=4):
        """Search for similar texts
        
        Args:
            query: Query text or embedding
            k: Number of results to return
        
        Returns:
            list: List of (document, metadata, score) tuples
        """
        if not self.collection:
            print("Vector store not initialized")
            return []
        
        # Search for similar texts
        results = self.collection.query(
            query_texts=[query],
            n_results=k
        )
        
        # Format results
        documents = results.get('documents', [[]])[0]
        metadatas = results.get('metadatas', [[]])[0]
        distances = results.get('distances', [[]])[0]
        
        # Convert distances to scores (1 - distance)
        scores = [1 - d for d in distances] if distances else [1.0] * len(documents)
        
        # Return as list of tuples
        return list(zip(documents, metadatas, scores))
    
    def delete_collection(self):
        """Delete the collection"""
        if self.client and self.collection:
            collection_name = self._get_collection_name()
            self.client.delete_collection(collection_name)
            self.collection = None
    
    def persist(self):
        """Persist the vector store to disk"""
        if self.client:
            self.client.persist()