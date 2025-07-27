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
from chromadb.config import Settings

class VectorStore:
    """Vector store using ChromaDB"""
    def __init__(self, config, file_path=None):
        """Initialize the vector store
        Args:
            config: Application configuration (dict or Config object)
            file_path: Path to the PDF file (for collection naming)
        """
        # --- FIX: Ensure config is treated as a dict-like object ---
        # The Config class provides .get(), so this should work.
        # But let's add a safety check or convert if needed.
        # If config is None, default to empty dict
        self.config = config if config is not None else {}
        # --- END FIX ---
        
        self.file_path = file_path
        self.client = None
        self.collection = None
        # Initialize vector store
        self._initialize_vector_store()

    def _initialize_vector_store(self):
        """Initialize the ChromaDB vector store"""
        try:
            # Get embeddings directory from config
            # --- This usage is correct ---
            data_dir = self.config.get('data_dir', './data')
            embeddings_dir = os.path.join(data_dir, 'embeddings')
            os.makedirs(embeddings_dir, exist_ok=True)
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(path=embeddings_dir)
            # Create or get collection for the file
            if self.file_path:
                collection_name = self._get_collection_name()
                self.collection = self.client.get_or_create_collection(
                    name=collection_name,
                    metadata={"file_path": self.file_path}
                )
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
            texts: List of texts to add (List[str])
            metadatas: List of metadata dictionaries (List[dict])
            ids: List of document IDs (List[str])
        Returns:
            list: List of document IDs
        """
        # --- FIX: Add defensive type checks ---
        if not isinstance(texts, (list, tuple)):
            print(f"Error in add_texts: 'texts' argument must be a list or tuple, got {type(texts)}")
            return None
        if metadatas is not None and not isinstance(metadatas, (list, tuple)):
             print(f"Error in add_texts: 'metadatas' argument must be a list, tuple, or None, got {type(metadatas)}")
             return None
        if ids is not None and not isinstance(ids, (list, tuple)):
             print(f"Error in add_texts: 'ids' argument must be a list, tuple, or None, got {type(ids)}")
             return None
        # --- END FIX ---
        
        if not self.collection:
            print("Vector store not initialized")
            return None
            
        # --- FIX: Ensure lengths match if metadatas or ids are provided ---
        if metadatas and len(metadatas) != len(texts):
            print(f"Error in add_texts: Length of metadatas ({len(metadatas)}) does not match length of texts ({len(texts)})")
            return None
        if ids and len(ids) != len(texts):
            print(f"Error in add_texts: Length of ids ({len(ids)}) does not match length of texts ({len(texts)})")
            return None
        # --- END FIX ---

        # Generate IDs if not provided
        if not ids:
            ids = [f"doc_{i}_{hash(str(text)) & 0x7FFFFFFF:08x}" for i, text in enumerate(texts)] # Safer hash for string

        # Add file hash to metadata
        if not metadatas:
            metadatas = [{} for _ in range(len(texts))]
        
        # --- FIX: Defensive check for metadatas list ---
        if not isinstance(metadatas, list) or len(metadatas) != len(texts):
             print(f"Error in add_texts: 'metadatas' is invalid or length mismatch after processing.")
             return None
        # --- END FIX ---
        
        file_hash = self.compute_file_hash() if self.file_path else "no_file"
        for meta in metadatas:
            # --- FIX: Ensure meta is a dict ---
            if not isinstance(meta, dict):
                print(f"Warning in add_texts: Metadata item is not a dict, skipping file_hash/source_file addition. Type: {type(meta)}")
                continue # Or handle differently?
            # --- END FIX ---
            meta['file_hash'] = file_hash
            meta['source_file'] = self.file_path or "unknown"

        try:
            # Add texts to collection
            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            return ids
        except Exception as e:
            print(f"Error adding texts to vector store: {e}")
            return None

    def similarity_search(self, query, k=4):
        """Search for similar texts
        Args:
            query: Query text (str)
            k: Number of results to return (int)
        Returns:
            list: List of (document, score, metadata) tuples
        """
        # --- FIX: Add input validation ---
        if not isinstance(query, str):
            print(f"Error in similarity_search: 'query' must be a string, got {type(query)}")
            return []
        if not isinstance(k, int) or k <= 0:
             print(f"Error in similarity_search: 'k' must be a positive integer, got {k} (type: {type(k)})")
             k = 4 # Default fallback
        # --- END FIX ---
        
        if not self.collection:
            print("Vector store not initialized")
            return []
        try:
            # Search for similar texts
            results = self.collection.query(
                query_texts=[query],
                n_results=k
            )
            # Format results
            documents = results.get('documents', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            distances = results.get('distances', [[]])[0]
            # Convert distances to scores (lower distance = higher similarity)
            scores = [1 / (1 + d) for d in distances] if distances else [0.0] * len(documents)
            # Return as list of tuples (document, score, metadata)
            return list(zip(documents, scores, metadatas))
        except Exception as e:
            print(f"Error in similarity search: {e}")
            return []

    def similarity_search_with_filter(self, query, filter_fn=None, k=3):
        """Search for similar chunks with optional metadata filtering.
        Args:
            query (str): The input question or text.
            filter_fn (function): A function to filter documents by metadata.
            k (int): Number of top results to return.
        Returns:
            list of (text, score, metadata)
        """
        # --- FIX: Add input validation ---
        if not isinstance(query, str):
            print(f"Error in similarity_search_with_filter: 'query' must be a string, got {type(query)}")
            return []
        if k is not None and (not isinstance(k, int) or k <= 0):
             print(f"Error in similarity_search_with_filter: 'k' must be a positive integer or None, got {k} (type: {type(k)})")
             k = 3 # Default fallback
        if filter_fn is not None and not callable(filter_fn):
             print(f"Error in similarity_search_with_filter: 'filter_fn' must be callable or None, got {type(filter_fn)}")
             filter_fn = None # Ignore invalid filter
        # --- END FIX ---
        
        if not self.collection:
            print("Vector store not initialized")
            return []
        try:
            # For ChromaDB, we need to use where clause for filtering
            # But for complex filtering, we fetch more and filter manually
            results = self.collection.query(
                query_texts=[query],
                n_results=100  # Fetch more so we can filter
            )
            if not results.get('documents'):
                return []
            # Extract results
            documents = results['documents'][0]
            distances = results.get('distances', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            # Convert distances to scores
            scores = [1 / (1 + d) for d in distances] if distances else [0.0] * len(documents)
            # Combine and filter
            combined_results = list(zip(documents, scores, metadatas))
            if filter_fn:
                filtered_results = [
                    (doc, score, meta)
                    for doc, score, meta in combined_results
                    if filter_fn(meta)
                ]
                # Sort by score (higher is better)
                filtered_results.sort(key=lambda x: x[1], reverse=True)
                return filtered_results[:k]
            else:
                # Sort by score and return top k
                combined_results.sort(key=lambda x: x[1], reverse=True)
                return combined_results[:k]
        except Exception as e:
            print(f"[VectorStore] Filtered similarity search error: {e}")
            return []

    def delete_collection(self):
        """Delete the collection"""
        if self.client and self.collection:
            try:
                collection_name = self._get_collection_name()
                self.client.delete_collection(name=collection_name)
                self.collection = None
                print(f"Collection {collection_name} deleted successfully")
            except Exception as e:
                print(f"Error deleting collection: {e}")

    def persist(self):
        """Persist changes (no-op for PersistentClient)"""
        # PersistentClient automatically persists, but we can force it
        if self.client:
            try:
                # This is a no-op in newer versions, but kept for compatibility
                pass
            except Exception as e:
                print(f"Warning: Error during persist: {e}")

    def has_existing_data(self):
        """Check if the vector store has any documents"""
        try:
            if self.collection:
                count_result = self.collection.count()
                return count_result > 0
            return False
        except Exception as e:
            print(f"Error checking for existing data: {e}")
            return False

    def compute_file_hash(self):
        """Compute MD5 hash of the current PDF file"""
        if not self.file_path or not os.path.exists(self.file_path):
            return "no_file"
        try:
            hasher = hashlib.md5()
            with open(self.file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            print(f"Error computing file hash: {e}")
            return "error_hash"

    def get_file_hash(self):
        """Retrieve stored file hash from metadata"""
        try:
            if self.collection:
                # Get a sample document to check its metadata
                sample_docs = self.collection.get(limit=1, include=['metadatas'])
                if sample_docs and sample_docs.get('metadatas'):
                    return sample_docs['metadatas'][0].get('file_hash', None)
        except Exception as e:
            print(f"[VectorStore] Error retrieving stored file hash: {e}")
        return None

    def get_document_count(self):
        """Get the number of documents in the collection"""
        try:
            if self.collection:
                return self.collection.count()
            return 0
        except Exception as e:
            print(f"Error getting document count: {e}")
            return 0

    def clear(self):
        """Clear all documents from the collection"""
        if self.collection:
            try:
                # Delete the entire collection and recreate it
                collection_name = self.collection.name
                self.client.delete_collection(name=collection_name)
                self.collection = self.client.get_or_create_collection(name=collection_name)
                print("Vector store cleared successfully")
            except Exception as e:
                print(f"Error clearing vector store: {e}")

    def add_texts_batch(self, texts, metadatas=None, ids=None, batch_size=100):
        """Add texts in batches to avoid memory issues"""
        # --- FIX: Add input validation ---
        if not isinstance(texts, (list, tuple)):
            print(f"Error in add_texts_batch: 'texts' argument must be a list or tuple, got {type(texts)}")
            return None
        if not isinstance(batch_size, int) or batch_size <= 0:
             print(f"Error in add_texts_batch: 'batch_size' must be a positive integer, got {batch_size}")
             batch_size = 100 # Default fallback
        # --- END FIX ---
        
        if not texts:
            return None
        all_ids = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size] if metadatas else None
            batch_ids = ids[i:i + batch_size] if ids else None
            batch_result = self.add_texts(batch_texts, batch_metadatas, batch_ids)
            if batch_result:
                all_ids.extend(batch_result)
        return all_ids
