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
        elif config_file:  # File specified but doesn't exist
            print(f"Warning: Config file {config_file} not found")

        # Override with environment variables
        self._load_from_env()

        # Create necessary directories
        self._create_directories()

        # Validate configuration
        self._validate_config()

    def _get_default_config(self):
        """Get default configuration

        Returns:
            dict: Default configuration
        """
        # Get application directory
        app_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

        return {
            # Data and cache directories
            'data_dir': os.path.join(app_dir, 'data'),
            'cache_dir': os.path.join(app_dir, 'data', 'cache'),
            'embeddings_dir': os.path.join(app_dir, 'data', 'embeddings'),
            'models_cache_dir': os.path.join(app_dir, 'data', 'models'),

            # PDF processing
            'pdf_chunk_size': 300,
            'pdf_chunk_overlap': 50,
            'pdf_cache_enabled': True,
            'max_page_cache_size': 10,

            # TTS settings
            'tts_model': 'tts_models/en/ljspeech/vits',
            'tts_rate': 1.0,
            'tts_volume': 1.0,

            # Embedding settings
            'embedding_model': 'all-MiniLM-L6-v2',
            'embedding_device': 'cpu',  # or 'cuda' if available

            # LLM settings

            'ollama_host': 'http://localhost',
            'ollama_port': 11434,
            'ollama_model': 'mistral:latest',
            'ollama_timeout': 60,

            # UI settings
            'window_width': 1024,
            'window_height': 768,
            'theme': 'light',  # or 'dark'

            # Performance settings
            'max_concurrent_threads': 4,
            'embedding_batch_size': 32
        }

    def _load_from_file(self, config_file):
        """Load configuration from file

        Args:
            config_file: Path to configuration file
        """
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
            # Merge with existing config
            self.config.update(file_config)
            print(f"Configuration loaded from {config_file}")
        except json.JSONDecodeError as e:
            print(f"Error parsing configuration file {config_file}: {e}")
        except IOError as e:
            print(f"Error reading configuration file {config_file}: {e}")

    def _load_from_env(self):
        """Load configuration from environment variables"""
        # Map environment variables to config keys
        env_mapping = {
            'SPOKENSENSE_DATA_DIR': 'data_dir',
            'SPOKENSENSE_CACHE_DIR': 'cache_dir',
            'SPOKENSENSE_EMBEDDINGS_DIR': 'embeddings_dir',
            'SPOKENSENSE_MODELS_CACHE_DIR': 'models_cache_dir',
            'SPOKENSENSE_PDF_CHUNK_SIZE': 'pdf_chunk_size',
            'SPOKENSENSE_PDF_CHUNK_OVERLAP': 'pdf_chunk_overlap',
            'SPOKENSENSE_PDF_CACHE_ENABLED': 'pdf_cache_enabled',
            'SPOKENSENSE_MAX_PAGE_CACHE_SIZE': 'max_page_cache_size',
            'SPOKENSENSE_TTS_MODEL': 'tts_model',
            'SPOKENSENSE_TTS_RATE': 'tts_rate',
            'SPOKENSENSE_TTS_VOLUME': 'tts_volume',
            'SPOKENSENSE_EMBEDDING_MODEL': 'embedding_model',
            'SPOKENSENSE_EMBEDDING_DEVICE': 'embedding_device',
            'SPOKENSENSE_OLLAMA_HOST': 'ollama_host',
            'SPOKENSENSE_OLLAMA_PORT': 'ollama_port',
            'SPOKENSENSE_OLLAMA_MODEL': 'ollama_model',
            'SPOKENSENSE_OLLAMA_TIMEOUT': 'ollama_timeout',
            'SPOKENSENSE_WINDOW_WIDTH': 'window_width',
            'SPOKENSENSE_WINDOW_HEIGHT': 'window_height',
            'SPOKENSENSE_THEME': 'theme',
            'SPOKENSENSE_MAX_CONCURRENT_THREADS': 'max_concurrent_threads',
            'SPOKENSENSE_EMBEDDING_BATCH_SIZE': 'embedding_batch_size'
        }

        # Update config with environment variables
        updated_keys = []
        for env_var, config_key in env_mapping.items():
            if env_var in os.environ:
                # Convert value to appropriate type
                value = os.environ[env_var]

                # Convert numeric values
                if config_key in ['pdf_chunk_size', 'pdf_chunk_overlap', 'ollama_port',
                                  'window_width', 'window_height', 'max_concurrent_threads',
                                  'embedding_batch_size', 'ollama_timeout']:
                    try:
                        value = int(value)
                    except ValueError:
                        print(f"Warning: Invalid integer value for {env_var}: {value}")
                        continue
                elif config_key in ['tts_rate', 'tts_volume']:
                    try:
                        value = float(value)
                    except ValueError:
                        print(f"Warning: Invalid float value for {env_var}: {value}")
                        continue
                elif config_key in ['pdf_cache_enabled']:
                    value = value.lower() in ['true', '1', 'yes', 'on']

                # Update config
                self.config[config_key] = value
                updated_keys.append(config_key)

        if updated_keys:
            print(f"Configuration updated from environment variables: {', '.join(updated_keys)}")

    def _create_directories(self):
        """Create necessary directories"""
        directories = [
            self.config['data_dir'],
            self.config['cache_dir'],
            self.config['embeddings_dir'],
            self.config['models_cache_dir']
        ]
        created_dirs = []
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                created_dirs.append(directory)
            except Exception as e:
                print(f"Error creating directory {directory}: {e}")

        if created_dirs:
            print(f"Created directories: {', '.join(created_dirs)}")

    def _validate_config(self):
        """Validate configuration values"""
        errors = []

        # Validate numeric values
        positive_ints = ['pdf_chunk_size', 'pdf_chunk_overlap', 'ollama_port',
                         'window_width', 'window_height', 'max_concurrent_threads']
        for key in positive_ints:
            if key in self.config and not isinstance(self.config[key], int):
                errors.append(f"{key} must be an integer")
            elif key in self.config and self.config[key] < 0:
                errors.append(f"{key} must be positive")

        # Validate float values
        float_values = ['tts_rate', 'tts_volume']
        for key in float_values:
            if key in self.config and not isinstance(self.config[key], (int, float)):
                errors.append(f"{key} must be a number")

        # Validate host/port
        if 'ollama_port' in self.config and not (1 <= self.config['ollama_port'] <= 65535):
            errors.append("ollama_port must be between 1 and 65535")

        # Validate theme
        if 'theme' in self.config and self.config['theme'] not in ['light', 'dark']:
            errors.append("theme must be 'light' or 'dark'")

        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f" - {error}")

    def get(self, key, default=None):
        """Get configuration value

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        return self.config.get(key, default)

    def __contains__(self, key):
        """
        Allows using the 'in' operator to check for keys.
        e.g., if 'some_key' in config:

        Args:
            key: The key to check for.

        Returns:
            bool: True if the key exists, False otherwise.
        """
        return key in self.config

    def set(self, key, value):
        """Set configuration value

        Args:
            key: Configuration key
            value: Configuration value
        """
        old_value = self.config.get(key)
        self.config[key] = value
        print(f"Configuration updated: {key} = {value} (was: {old_value})")

    def save(self, config_file):
        """Save configuration to file

        Args:
            config_file: Path to configuration file
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=4, sort_keys=True)
            print(f"Configuration saved to {config_file}")
        except IOError as e:
            print(f"Error saving configuration to file {config_file}: {e}")
        except Exception as e:
            print(f"Unexpected error saving configuration: {e}")

    def get_all(self):
        """Get all configuration values

        Returns:
            dict: All configuration values
        """
        return self.config.copy()

    def reload(self, config_file=None):
        """Reload configuration

        Args:
            config_file: Path to configuration file (optional)
        """
        print("Reloading configuration...")
        # Reset to defaults
        self.config = self._get_default_config()

        # Reload from file if provided
        if config_file and os.path.exists(config_file):
            self._load_from_file(config_file)

        # Reload from environment
        self._load_from_env()

        # Recreate directories
        self._create_directories()

        # Revalidate
        self._validate_config()
        print("Configuration reloaded successfully")

    def generate_template(self, template_file='config_template.json'):
        """Generate a configuration template file"""
        template = {
            "_comment": "SpokenSense Configuration Template",
            "data_dir": "./data",
            "cache_dir": "./data/cache",
            "embeddings_dir": "./data/embeddings",
            "models_cache_dir": "./data/models",
            "pdf_chunk_size": 300,
            "pdf_chunk_overlap": 50,
            "tts_model": "tts_models/en/ljspeech/tacotron2-DDC",
            "tts_rate": 1.0,
            "tts_volume": 1.0,
            "embedding_model": "all-MiniLM-L6-v2",
            "embedding_device": "cpu",  # or 'cuda' if available
            "ollama_host": "http://localhost",
            "ollama_port": 11434,
            "ollama_model": "nous-hermes2",
            "ollama_timeout": 60,
            "window_width": 1024,
            "window_height": 768,
            "theme": "light",  # or 'dark'
            "max_concurrent_threads": 4,
            "embedding_batch_size": 32
        }

        try:
            with open(template_file, 'w') as f:
                json.dump(template, f, indent=4)
            print(f"Configuration template generated: {template_file}")
        except Exception as e:
            print(f"Error generating template: {e}")
