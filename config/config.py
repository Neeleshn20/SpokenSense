#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration Manager for SpokenSense

This module provides functionality for managing application configuration,
including loading from files and environment variables.
"""

import os
import json
from dotenv import load_dotenv


class Config:
    """Configuration manager for SpokenSense"""
    
    def __init__(self, config_file=None):
        """Initialize the configuration manager
        
        Args:
            config_file: Path to configuration file (optional)
        """
        # Load environment variables
        load_dotenv()
        
        # Set default configuration
        self.config = self._get_default_config()
        
        # Load configuration from file if provided
        if config_file and os.path.exists(config_file):
            self._load_from_file(config_file)
        
        # Override with environment variables
        self._load_from_env()
        
        # Create necessary directories
        self._create_directories()
    
    def _get_default_config(self):
        """Get default configuration
        
        Returns:
            dict: Default configuration
        """
        # Get application directory
        app_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        data_dir = os.path.join(app_dir, 'data')
        
        return {
            # Application paths
            'app_dir': app_dir,
            'data_dir': data_dir,
            'cache_dir': os.path.join(data_dir, 'cache'),
            'embeddings_dir': os.path.join(data_dir, 'embeddings'),
            
            # PDF processing
            'pdf_chunk_size': 300,
            'pdf_chunk_overlap': 50,
            
            # TTS settings
            'tts_model': 'tts_models/en/ljspeech/tacotron2-DDC',
            'tts_rate': 1.0,
            'tts_voice': None,
            
            # Embedding settings
            'embedding_model': 'all-MiniLM-L6-v2',
            
            # LLM settings
            'ollama_host': 'http://localhost',
            'ollama_port': 11434,
            'ollama_model': 'nous-hermes2',
            
            # UI settings
            'window_width': 1024,
            'window_height': 768
        }
    
    def _load_from_file(self, config_file):
        """Load configuration from file
        
        Args:
            config_file: Path to configuration file
        """
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                self.config.update(file_config)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading configuration from file: {e}")
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        # Map environment variables to config keys
        env_mapping = {
            'SPOKENSENSE_DATA_DIR': 'data_dir',
            'SPOKENSENSE_CACHE_DIR': 'cache_dir',
            'SPOKENSENSE_EMBEDDINGS_DIR': 'embeddings_dir',
            'SPOKENSENSE_PDF_CHUNK_SIZE': 'pdf_chunk_size',
            'SPOKENSENSE_PDF_CHUNK_OVERLAP': 'pdf_chunk_overlap',
            'SPOKENSENSE_TTS_MODEL': 'tts_model',
            'SPOKENSENSE_TTS_RATE': 'tts_rate',
            'SPOKENSENSE_TTS_VOICE': 'tts_voice',
            'SPOKENSENSE_EMBEDDING_MODEL': 'embedding_model',
            'SPOKENSENSE_OLLAMA_HOST': 'ollama_host',
            'SPOKENSENSE_OLLAMA_PORT': 'ollama_port',
            'SPOKENSENSE_OLLAMA_MODEL': 'ollama_model',
            'SPOKENSENSE_WINDOW_WIDTH': 'window_width',
            'SPOKENSENSE_WINDOW_HEIGHT': 'window_height'
        }
        
        # Update config with environment variables
        for env_var, config_key in env_mapping.items():
            if env_var in os.environ:
                # Convert value to appropriate type
                value = os.environ[env_var]
                
                # Convert numeric values
                if config_key in ['pdf_chunk_size', 'pdf_chunk_overlap', 'ollama_port', 'window_width', 'window_height']:
                    try:
                        value = int(value)
                    except ValueError:
                        pass
                elif config_key in ['tts_rate']:
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                
                # Update config
                self.config[config_key] = value
    
    def _create_directories(self):
        """Create necessary directories"""
        directories = [
            self.config['data_dir'],
            self.config['cache_dir'],
            self.config['embeddings_dir']
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def get(self, key, default=None):
        """Get configuration value
        
        Args:
            key: Configuration key
            default: Default value if key not found
        
        Returns:
            Configuration value
        """
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set configuration value
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self.config[key] = value
    
    def save(self, config_file):
        """Save configuration to file
        
        Args:
            config_file: Path to configuration file
        """
        try:
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except IOError as e:
            print(f"Error saving configuration to file: {e}")