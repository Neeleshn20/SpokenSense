#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM Question Answering for SpokenSense

This module provides question answering functionality using RAG
(Retrieval Augmented Generation) with local LLMs.
"""

import os
import threading
import logging
from PyQt5.QtCore import QObject, pyqtSignal

# Ensure these modules exist in the same package structure
# Make sure the imports match your project structure
from ai.embedder import TextEmbedder
from ai.vector_store import VectorStore
from ai.llm_wrapper import OllamaLLM

# Set up logging
logger = logging.getLogger(__name__)

class LLMQA(QObject):
    """
    Question answering using RAG with local LLMs.
    Emits signals for asynchronous operation.
    """
    answer_ready = pyqtSignal(str)
    processing_status = pyqtSignal(str)

    def __init__(self, file_path, config):
        """
        Initialize the QA system.

        Args:
            file_path (str): Path to the PDF file.
            config (dict or Config object): Application configuration.
        """
        super().__init__()
        self.file_path = file_path
        # Ensure config is a dict-like object, defaulting to empty dict if None
        # This handles cases where config might be None or the Config object
        self.config = config if config is not None else {}

        # Validate required config keys based on your config.py defaults
        # config.py uses 'ollama_model', 'embedding_model'
        required_keys = ['embedding_model', 'ollama_model']
        missing_keys = [key for key in required_keys if key not in self.config]
        if missing_keys:
             logger.warning(f"Missing config keys for LLMQA: {missing_keys}. Using defaults where possible.")

        # Initialize AI components
        try:
            logger.debug("Initializing TextEmbedder...")
            self.embedder = TextEmbedder(self.config)
            logger.debug("Initializing VectorStore...")
            self.vector_store = VectorStore(self.config, file_path)
            logger.debug("Initializing OllamaLLM...")
            self.llm = OllamaLLM(self.config)
            logger.info("All AI components initialized successfully.")
        except Exception as e:
            logger.critical(f"Error initializing AI components: {e}", exc_info=True)
            # Re-raise to signal failure in LLMQA setup to the caller
            raise RuntimeError(f"Failed to initialize LLMQA components: {e}") from e

        self.is_processed = False
        self.use_full_context = True

    def set_context_scope(self, use_full):
        """
        Toggle between full document vs local (page-wise) QA.

        Args:
            use_full (bool): If True, use full document context.
        """
        self.use_full_context = use_full
        logger.debug(f"Context scope set to {'full document' if use_full else 'page-wise'}")

    def process_document(self, chunks):
        """
        Process document chunks and add them to the vector store.

        Args:
            chunks (list): List of text chunks (str or dict) from the document.
        """
        logger.info("Starting document processing...")
        if not chunks:
            msg = "No chunks to process."
            logger.info(msg)
            self.processing_status.emit(msg)
            return # Early return if no data

        self.processing_status.emit("Processing document...")
        logger.debug(f"Received {len(chunks)} chunks for processing.")

        try:
            # Check if reprocessing is needed based on file hash
            if self.vector_store.has_existing_data():
                try:
                    stored_hash = self.vector_store.get_file_hash()
                    current_hash = self.vector_store.compute_file_hash()
                    if stored_hash != current_hash:
                        msg = "PDF content changed — reprocessing."
                        logger.info(msg)
                        self.processing_status.emit(msg)
                        self.vector_store.clear()
                        logger.debug("Vector store cleared for reprocessing.")
                except Exception as e:
                    logger.error(f"Error checking file hash for reprocessing: {e}. Continuing with processing.")

            # Prepare data for vector store using list comprehensions for clarity and potential speed
            text_chunks = [
                chunk.get('text', str(chunk)) if isinstance(chunk, dict) else str(chunk)
                for chunk in chunks
            ]

            metadatas = [
                {
                    'source': self.file_path,
                    'chunk_id': i,
                    'page': chunk.get('page', -1) if isinstance(chunk, dict) else -1
                }
                for i, chunk in enumerate(chunks)
            ]

            # Add texts to vector store
            logger.debug("Adding texts to vector store...")
            ids = self.vector_store.add_texts(text_chunks, metadatas=metadatas)
            if ids is None:
                 error_msg = "Failed to add texts to vector store."
                 logger.error(error_msg)
                 self.processing_status.emit(f"Error: {error_msg}")
                 # Do not set is_processed to True if it failed
                 return

            self.is_processed = True
            success_msg = f"Document processing complete. Added {len(ids)} chunks."
            logger.info(success_msg)
            self.processing_status.emit(success_msg)

        except Exception as e:
            error_msg = f"Error processing document: {e}"
            logger.error(error_msg, exc_info=True) # Log full traceback
            self.processing_status.emit(f"Error: {error_msg}")
            # Ensure is_processed reflects the failure state if it was set True earlier in the try block
            # It wasn't in this version, so no need to reset here unless logic changes.

    def _ask_sync(self, question, page=None, k=3, max_retries=2):
        """
        Internal blocking version of ask.

        Args:
            question (str): The question to ask.
            page (int, optional): Current page number for context filtering.
            k (int): Number of chunks to retrieve.
            max_retries (int): Max number of LLM call retries.

        Returns:
            str: The answer generated by the LLM.
        """
        if not self.is_processed:
            logger.info("Document not yet processed, returning wait message.")
            return "Please wait while I process the document..."

        try:
            logger.info(f"Asking question: '{question[:50]}...'") # Log first 50 chars
            # Search for relevant chunks
            if self.use_full_context or page is None:
                logger.debug("Performing full-context similarity search...")
                results = self.vector_store.similarity_search(question, k=k)
            else:
                logger.debug(f"Performing page-wise similarity search (page {page})...")
                results = self.vector_store.similarity_search_with_filter(
                    question,
                    filter_fn=lambda meta: meta.get("page", -1) == page,
                    k=k
                )

            if not results:
                no_info_msg = "I couldn't find any relevant information in the document."
                logger.info(no_info_msg)
                return no_info_msg

            # Extract documents for context
            documents = [doc for doc, _, _ in results]
            # Limit context length to prevent prompt overflow and improve speed
            # Join with newlines for better LLM understanding of separate snippets
            context = "\n\n---\n\n".join(documents[:3])
            if not context.strip():
                 empty_context_msg = "Found relevant chunks, but they were empty."
                 logger.warning(empty_context_msg)
                 return empty_context_msg

            # Construct prompt for LLM
            system_prompt = (
                "You are a helpful AI assistant that answers questions about documents. "
                "Use only the provided context to answer the question. "
                "If the answer is not in the context, say that you don't know. "
                "Keep your answers concise and to the point."
            )

            prompt = f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"

            # Generate answer with retry mechanism
            retries = 0
            last_error = None

            while retries <= max_retries:
                try:
                    logger.debug(f"Calling LLM (attempt {retries + 1}/{max_retries + 1})...")
                    answer = self.llm.generate(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        max_tokens=512,
                        temperature=0.3
                    )
                    logger.debug("LLM call completed.")

                    # Check if the LLM returned a successful response
                    if answer and not str(answer).strip().startswith("Error:"):
                        final_answer = answer.strip()
                        logger.info("LLM answer generated successfully.")
                        return final_answer
                    else:
                        # Capture the error message returned by the LLM wrapper
                        last_error = str(answer).strip() if answer else "Empty response received"
                        logger.warning(f"LLM returned error/empty response: {last_error}")
                        retries += 1
                        if retries <= max_retries:
                             logger.info(f"Retrying LLM call... ({retries + 1}/{max_retries + 1})")

                except Exception as e: # Catch exceptions during the LLM call itself
                    last_error = f"Exception during LLM call: {e}"
                    logger.error(last_error, exc_info=True) # Log full traceback
                    retries += 1
                    if retries <= max_retries:
                        logger.info(f"Retrying LLM call... ({retries + 1}/{max_retries + 1})")

            # If all retries failed, return a message with the last error
            final_error_msg = f"I'm having trouble answering your question. Please try again later. Last error: {last_error}"
            logger.error(f"All LLM retries failed. Final error: {last_error}")
            return final_error_msg

        except Exception as e: # Catch any other unexpected errors in _ask_sync
            unexpected_error_msg = f"I'm having trouble processing your question. An unexpected error occurred: {e}"
            logger.critical(unexpected_error_msg, exc_info=True) # Log full traceback
            return unexpected_error_msg

    def ask(self, question, page=None, k=3):
        """
        Non-blocking version of ask. Emits `answer_ready` signal when done.

        Args:
            question (str): The question to ask.
            page (int, optional): Current page number for context filtering.
            k (int): Number of chunks to retrieve.
        """
        logger.debug(f"Starting non-blocking ask for question: '{question[:30]}...'")

        def run():
            """Target function for the worker thread."""
            try:
                answer = self._ask_sync(question, page, k)
                logger.debug("Emitting answer via signal.")
                self.answer_ready.emit(answer)
            except Exception as e: # Catch unexpected errors in the worker thread
                thread_error_msg = f"An unexpected error occurred in the worker thread: {e}"
                logger.critical(thread_error_msg, exc_info=True)
                self.answer_ready.emit(thread_error_msg) # Emit error to UI

        # Start the worker thread
        thread = threading.Thread(target=run, daemon=True, name=f"LLMQA_Ask_Thread_{question[:10]}")
        logger.debug("Starting worker thread for question.")
        thread.start()

    def cleanup(self):
        """Clean up resources, persisting the vector store."""
        logger.debug("Cleaning up LLMQA resources...")
        try:
            if hasattr(self, 'vector_store') and self.vector_store:
                logger.debug("Persisting vector store...")
                self.vector_store.persist()
                logger.debug("Vector store persisted.")
            # Note: TextEmbedder and OllamaLLM don't seem to have specific cleanup in provided code
            logger.debug("LLMQA cleanup completed.")
        except Exception as e:
            logger.error(f"Error during LLMQA cleanup: {e}", exc_info=True)

    def get_document_stats(self):
        """
        Get statistics about the processed document.

        Returns:
            dict: Document statistics or status.
        """
        if not self.is_processed:
            return {"status": "Not processed"}

        try:
            logger.debug("Getting document statistics...")
            count = self.vector_store.get_document_count()
            stats = {
                "status": "Processed",
                "chunk_count": count,
                "file_path": self.file_path
            }
            logger.debug(f"Document stats retrieved: {stats}")
            return stats
        except Exception as e:
            # Ensure any error in getting stats is caught and reported
            error_info = {"status": "Error", "error": f"Failed to get stats: {str(e)}"}
            logger.error(f"Error getting document stats: {e}", exc_info=True)
            return error_info # Return error info instead of raising
