#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Question Answering for SpokenSense

This module provides question answering functionality using RAG
(Retrieval Augmented Generation) with local LLMs.
"""

import os
from .embedder import TextEmbedder
from .vector_store import VectorStore
from .llm_wrapper import OllamaLLM


class LLMQA:
    """Question answering using RAG with local LLMs"""
    
    def __init__(self, file_path, config):
        """Initialize the QA system
        
        Args:
            file_path: Path to the PDF file
            config: Application configuration
        """
        self.file_path = file_path
        self.config = config
        
        # Initialize components
        self.embedder = TextEmbedder(config)
        self.vector_store = VectorStore(config, file_path)
        self.llm = OllamaLLM(config)
        
        # Track if the document has been processed
        self.is_processed = False
    
    def process_document(self, chunks):
        """Process document chunks and add to vector store
        
        Args:
            chunks: List of text chunks from the document
        """
        if not chunks:
            print("No chunks to process")
            return
        
        # Generate embeddings for chunks
        try:
            # Add chunks to vector store with metadata
            metadatas = [{'source': self.file_path, 'chunk_id': i} for i in range(len(chunks))]
            self.vector_store.add_texts(chunks, metadatas=metadatas)
            
            # Mark as processed
            self.is_processed = True
            
        except Exception as e:
            print(f"Error processing document: {e}")
    
    def ask(self, question, page=None, k=3):
        """Ask a question about the document
        
        Args:
            question: Question to ask
            page: Current page number (optional)
            k: Number of chunks to retrieve
        
        Returns:
            str: Answer to the question
        """
        if not self.is_processed:
            return "Please wait while I process the document..."
        
        try:
            # Search for relevant chunks
            results = self.vector_store.similarity_search(question, k=k)
            
            if not results:
                return "I couldn't find any relevant information in the document."
            
            # Extract documents and scores
            documents = [doc for doc, _, _ in results]
            
            # Construct context from retrieved documents
            context = "\n\n".join(documents)
            
            # Construct prompt for LLM
            system_prompt = (
                "You are a helpful AI assistant that answers questions about documents. "
                "Use only the provided context to answer the question. "
                "If the answer is not in the context, say that you don't know. "
                "Keep your answers concise and to the point."
            )
            
            prompt = f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
            
            # Generate answer
            answer = self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=512,
                temperature=0.3
            )
            
            return answer
            
        except Exception as e:
            print(f"Error answering question: {e}")
            return f"Error: {str(e)}"
    
    def cleanup(self):
        """Clean up resources"""
        # Persist vector store
        if hasattr(self, 'vector_store') and self.vector_store:
            self.vector_store.persist()