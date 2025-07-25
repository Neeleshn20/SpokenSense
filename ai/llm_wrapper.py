#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Wrapper for SpokenSense

This module provides a wrapper for interacting with local LLMs via Ollama.
"""

import requests
import json


class OllamaLLM:
    """Wrapper for Ollama LLM API"""
    
    def __init__(self, config):
        """Initialize the LLM wrapper
        
        Args:
            config: Application configuration
        """
        self.config = config
        
        # Get Ollama settings from config
        self.host = config.get('ollama_host', 'http://localhost')
        self.port = config.get('ollama_port', 11434)
        self.model = config.get('ollama_model', 'nous-hermes2')
        
        # Construct API URL
        self.api_url = f"{self.host}:{self.port}/api/generate"
    
    def generate(self, prompt, system_prompt=None, max_tokens=1024, temperature=0.7):
        """Generate text using the LLM
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
        
        Returns:
            str: Generated text
        """
        # Prepare request payload
        payload = {
            "model": self.model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # Add system prompt if provided
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            # Send request to Ollama API
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            
            # Extract generated text
            return result.get('response', '')
            
        except requests.exceptions.RequestException as e:
            print(f"Error calling Ollama API: {e}")
            return f"Error: {str(e)}"
    
    def chat(self, messages, max_tokens=1024, temperature=0.7):
        """Generate a chat response using the LLM
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
        
        Returns:
            str: Generated response
        """
        # Extract system message if present
        system_prompt = None
        chat_messages = []
        
        for message in messages:
            if message['role'] == 'system':
                system_prompt = message['content']
            else:
                chat_messages.append(message)
        
        # Construct chat prompt
        chat_prompt = ""
        
        for message in chat_messages:
            role = message['role']
            content = message['content']
            
            if role == 'user':
                chat_prompt += f"User: {content}\n"
            elif role == 'assistant':
                chat_prompt += f"Assistant: {content}\n"
        
        # Add final user prompt marker if needed
        if chat_messages and chat_messages[-1]['role'] == 'user':
            chat_prompt += "Assistant: "
        
        # Generate response
        return self.generate(
            prompt=chat_prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )