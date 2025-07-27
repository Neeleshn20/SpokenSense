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
        self.config = config or {}
        
        # Get Ollama settings from config
        self.host = self.config.get('ollama_host', 'http://localhost')
        self.port = self.config.get('ollama_port', 11434)
        self.model = self.config.get('ollama_model', 'nous-hermes2')
        
        # Construct API URLs
        self.generate_url = f"{self.host}:{self.port}/api/generate"
        self.chat_url = f"{self.host}:{self.port}/api/chat"
        # Validate that Ollama is accessible
        if not self._check_ollama_connection():
            print("Warning: Cannot connect to Ollama server. Please ensure Ollama is running.")
        
        # Validate that model is available
        if not self.is_model_available():
            print(f"Warning: Model '{self.model}' not found. Available models: {self.list_models()}")

    def _check_ollama_connection(self):
        """Check if Ollama server is accessible"""
        try:
            version_url = f"{self.host}:{self.port}/api/version"
            response = requests.get(version_url, timeout=5)
            return response.status_code == 200
        except:
            return False
    def generate(self, prompt, system_prompt=None, max_tokens=None, temperature=0.7, stream=False):
        """Generate text using the LLM
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            max_tokens: Maximum number of tokens to generate (note: Ollama uses 'num_predict')
            temperature: Sampling temperature
            stream: Whether to stream the response
        
        Returns:
            str: Generated text
        """
        # Prepare request payload - Ollama specific format
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,  # We want the full response
            "options": {
                "temperature": temperature
            }
        }
        
        # Add system prompt if provided
        if system_prompt:
            payload["system"] = system_prompt
            
        # Add max tokens if provided (Ollama uses 'num_predict')
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        try:
            # Send request to Ollama API with timeout
            response = requests.post(
                self.generate_url, 
                json=payload, 
                timeout=60  # Increased timeout for LLM generation
            )
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            
            # Extract generated text
            generated_text = result.get('response', '')
            return generated_text.strip()
            
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error to Ollama API: {e}")
            return "Error: Could not connect to the Ollama server. Please make sure Ollama is running and accessible."
        except requests.exceptions.Timeout as e:
            print(f"Timeout error calling Ollama API: {e}")
            return "Error: Request to Ollama timed out. The model might be taking too long to respond."
        except requests.exceptions.RequestException as e:
            print(f"Error calling Ollama API: {e}")
            return f"Error: {str(e)}"
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response: {e}")
            return "Error: Invalid response from Ollama server."
        except Exception as e:
            print(f"Unexpected error: {e}")
            return f"Error: Unexpected error occurred - {str(e)}"
    
    def chat(self, messages, max_tokens=None, temperature=0.7):
        """Generate a chat response using the LLM
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
        
        Returns:
            str: Generated response
        """
        # Prepare request payload for chat API
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        
        # Add max tokens if provided
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        try:
            # Send request to Ollama chat API
            response = requests.post(
                self.chat_url, 
                json=payload, 
                timeout=60
            )
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            
            # Extract generated text
            message_content = result.get('message', {})
            generated_text = message_content.get('content', '')
            return generated_text.strip()
            
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error to Ollama chat API: {e}")
            return "Error: Could not connect to the Ollama server. Please make sure Ollama is running and accessible."
        except requests.exceptions.Timeout as e:
            print(f"Timeout error calling Ollama chat API: {e}")
            return "Error: Request to Ollama timed out. The model might be taking too long to respond."
        except requests.exceptions.RequestException as e:
            print(f"Error calling Ollama chat API: {e}")
            return f"Error: {str(e)}"
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response: {e}")
            return "Error: Invalid response from Ollama server."
        except Exception as e:
            print(f"Unexpected error: {e}")
            return f"Error: Unexpected error occurred - {str(e)}"
    
    def list_models(self):
        """List available models on Ollama server
        
        Returns:
            list: List of available models
        """
        try:
            list_url = f"{self.host}:{self.port}/api/tags"
            response = requests.get(list_url, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            models = [model['name'] for model in result.get('models', [])]
            return models
            
        except Exception as e:
            print(f"Error listing models: {e}")
            return []
    
    def is_model_available(self):
        """Check if the configured model is available
        
        Returns:
            bool: True if model is available, False otherwise
        """
        try:
            available_models = self.list_models()
            return self.model in available_models
        except Exception as e:
            print(f"Error checking model availability: {e}")
            return False
    def generate_stream(self, prompt, system_prompt=None, temperature=0.7):
        """Generate text with streaming support
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Sampling temperature
        
        Yields:
            str: Chunks of generated text
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = requests.post(
                self.generate_url, 
                json=payload, 
                timeout=60,
                stream=True
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        if 'response' in chunk:
                            yield chunk['response']
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            yield f"Error: {str(e)}"