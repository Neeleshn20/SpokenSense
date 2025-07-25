#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Coqui TTS Engine for SpokenSense

This module provides text-to-speech functionality using Coqui TTS,
with word-level synchronization for highlighting during playback.
"""

import os
import time
import threading
import queue
import numpy as np
from TTS.api import TTS
from PyQt5.QtCore import QObject, pyqtSignal, QTimer


class CoquiTTS(QObject):
    """Text-to-speech engine using Coqui TTS"""
    
    # Signal for word callback
    word_signal = pyqtSignal(int)
    
    def __init__(self, config):
        """Initialize the TTS engine
        
        Args:
            config: Application configuration
        """
        super().__init__()
        
        self.config = config
        self.tts = None
        self.audio_queue = queue.Queue()
        self.is_playing = False
        self.is_paused = False
        self.current_text = ""
        self.word_boxes = None
        self.word_callback = None
        self.current_word_index = -1
        
        # Initialize TTS engine
        self._initialize_tts()
        
        # Create playback thread
        self.playback_thread = None
    
    def _initialize_tts(self):
        """Initialize the Coqui TTS engine"""
        try:
            # Get TTS model from config
            model_name = self.config.get('tts_model', 'tts_models/en/ljspeech/tacotron2-DDC')
            
            # Initialize TTS with model_name as a named parameter
            # This ensures compatibility with TTS 0.15.0
            self.tts = TTS(model_name=model_name)
            
            # Set voice if specified - use get() method instead of 'in' operator
            tts_voice = self.config.get('tts_voice')
            if tts_voice is not None and tts_voice != '':
                self.tts.voice = tts_voice

            # Set speaking rate if specified - use get() method instead of 'in' operator
            tts_rate = self.config.get('tts_rate')
            if tts_rate is not None and tts_rate != '':
                self.tts.rate = float(tts_rate)
            
        except Exception as e:
            print(f"Error initializing TTS: {e}")
            self.tts = None
    
    def set_word_callback(self, callback):
        """Set callback function for word synchronization
        
        Args:
            callback: Function to call when a new word is spoken
        """
        self.word_callback = callback
        
        # Connect signal to callback
        self.word_signal.connect(callback)
    
    def speak(self, text, word_boxes=None):
        """Speak text with word synchronization
        
        Args:
            text: Text to speak
            word_boxes: List of word bounding boxes for synchronization
        """
        if not self.tts:
            print("TTS engine not initialized")
            return
        
        # Stop any current playback
        self.stop()
        
        # Set text and word boxes
        self.current_text = text
        self.word_boxes = word_boxes
        self.current_word_index = -1
        
        # Start playback thread
        self.is_playing = True
        self.is_paused = False
        self.playback_thread = threading.Thread(target=self._playback_worker)
        self.playback_thread.daemon = True
        self.playback_thread.start()
    
    def pause(self):
        """Pause TTS playback"""
        self.is_paused = True
    
    def resume(self):
        """Resume TTS playback"""
        self.is_paused = False
    
    def stop(self):
        """Stop TTS playback"""
        self.is_playing = False
        self.is_paused = False
        self.current_word_index = -1
        
        # Clear audio queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
    
    def _playback_worker(self):
        """Worker thread for TTS playback"""
        try:
            print("Starting TTS playback worker...")
            # Generate audio
            print("Generating audio with TTS...")
            wav = self.tts.tts(self.current_text)
            print(f"Audio generated, length: {len(wav)} samples, type: {type(wav)}")
            
            # Estimate word timings
            print("Estimating word timings...")
            word_timings = self._estimate_word_timings(self.current_text, len(wav))
            print(f"Word timings estimated: {len(word_timings)} words")
            
            # Play audio with word synchronization
            print("Playing audio with word synchronization...")
            self._play_with_word_sync(wav, word_timings)
            print("Audio playback completed")
        except Exception as e:
            print(f"TTS playback worker error: {e}")
            import traceback
            traceback.print_exc()
            
        except Exception as e:
            print(f"TTS playback error: {e}")
            import traceback
            traceback.print_exc()
    
    def _estimate_word_timings(self, text, audio_length):
        """Estimate word timings based on text and audio length
        
        Args:
            text: Text to speak
            audio_length: Length of audio in samples
        
        Returns:
            list: Estimated start time for each word in seconds
        """
        # Split text into words
        words = text.split()
        
        # Calculate total characters
        total_chars = sum(len(word) for word in words)
        
        # Estimate audio duration in seconds (assuming 22050 Hz sample rate)
        audio_duration = audio_length / 22050
        
        # Estimate time per character
        time_per_char = audio_duration / total_chars
        
        # Calculate word timings
        word_timings = []
        current_time = 0
        
        for word in words:
            word_timings.append(current_time)
            current_time += len(word) * time_per_char + 0.1  # Add small gap between words
        
        return word_timings
    
    def _play_with_word_sync(self, wav, word_timings):
        """Play audio with word synchronization
        
        Args:
            wav: Audio data
            word_timings: List of word start times in seconds
        """
        try:
            import sounddevice as sd
            
            # Set sample rate
            sample_rate = 22050
            
            # Check audio data
            if len(wav) == 0:
                print("Error: Audio data is empty")
                return
                
            print(f"Starting audio playback with sample rate {sample_rate} Hz")
            print(f"Audio data shape: {wav.shape if hasattr(wav, 'shape') else 'unknown'}, dtype: {wav.dtype if hasattr(wav, 'dtype') else type(wav)}")
            print(f"Default audio device: {sd.default.device}")
            
            try:
                # Start playback
                sd.play(wav, sample_rate)
                print("Audio playback started")
            except Exception as e:
                print(f"Error during sd.play: {e}")
                import traceback
                traceback.print_exc()
        except Exception as e:
            print(f"Error starting audio playback: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Synchronize with words
        start_time = time.time()
        
        for i, word_time in enumerate(word_timings):
            # Wait until word time is reached
            while time.time() - start_time < word_time:
                # Check if playback is stopped or paused
                if not self.is_playing:
                    sd.stop()
                    return
                
                if self.is_paused:
                    sd.stop()
                    # Wait until resumed
                    while self.is_paused and self.is_playing:
                        time.sleep(0.1)
                    
                    if not self.is_playing:
                        return
                    
                    # Resume playback from current position
                    position = word_time
                    sd.play(wav[int(position * sample_rate):], sample_rate)
                    start_time = time.time() - position
                
                time.sleep(0.01)
            
            # Update current word index
            self.current_word_index = i
            
            # Emit signal for word callback
            self.word_signal.emit(i)
        
        # Wait for playback to finish
        sd.wait()
        
        # Reset state
        self.is_playing = False
        self.current_word_index = -1
    
    def cleanup(self):
        """Clean up resources"""
        self.stop()