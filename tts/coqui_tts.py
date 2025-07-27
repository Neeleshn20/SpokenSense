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
import logging
from typing import Optional, List, Tuple, Callable, Any

# --- Dependency Checks ---
_MISSING_DEPS = []
try:
    import numpy as np
except ImportError:
    _MISSING_DEPS.append("numpy")

try:
    from TTS.api import TTS
except ImportError:
    _MISSING_DEPS.append("TTS")

try:
    import sounddevice as sd
except ImportError:
    _MISSING_DEPS.append("sounddevice")

if _MISSING_DEPS:
    raise ImportError(
        f"Missing required dependencies for CoquiTTS: {', '.join(_MISSING_DEPS)}. "
        f"Please install them using pip."
    )

from PyQt5.QtCore import QObject, pyqtSignal

# Configure logger for this module
logger = logging.getLogger(__name__)


class CoquiTTS(QObject):
    """
    Text-to-speech engine using Coqui TTS with word-level synchronization.
    """

    # Signal emitted when a new word should be highlighted.
    # The argument is the 0-based index of the word in the current text chunk.
    word_signal = pyqtSignal(int)

    def __init__(self, config: dict):
        """
        Initialize the TTS engine.

        Args:
            config: Application configuration dictionary.
        """
        super().__init__()
        self.config = config or {}

        # TTS Engine Instance
        self.tts: Optional[TTS] = None

        # Playback State
        self.audio_queue = queue.Queue()
        self.is_playing = False
        self.is_paused = False
        self.stopped = False

        # Text & Data
        self.current_text = ""
        self.word_boxes: Optional[List[Tuple[float, float, float, float]]] = None
        self.text_chunks: Optional[List[str]] = None
        self.current_chunk_index = -1

        # Threading
        self.preprocess_thread: Optional[threading.Thread] = None
        self.playback_thread: Optional[threading.Thread] = None

        # Callback (Connected via signal)
        self.word_callback: Optional[Callable[[int], Any]] = None

        # Initialize the TTS engine
        self._initialize_tts()

    def _initialize_tts(self):
        """Initialize the Coqui TTS engine."""
        try:
            model_name = self.config.get('tts_model', 'tts_models/en/ljspeech/vits')
            logger.info(f"Initializing Coqui TTS with model: {model_name}")

            # Initialize TTS with model_name as a named parameter
            self.tts = TTS(model_name=model_name)

            # Set voice if specified
            tts_voice = self.config.get('tts_voice')
            if tts_voice:
                logger.info(f"Setting TTS voice to: {tts_voice}")
                self.tts.voice = tts_voice

            # Set speaking rate if specified
            tts_rate = self.config.get('tts_rate')
            if tts_rate is not None:
                try:
                    rate_float = float(tts_rate)
                    logger.info(f"Setting TTS rate to: {rate_float}")
                    self.tts.rate = rate_float
                except (ValueError, TypeError):
                    logger.warning(f"Invalid TTS rate value: {tts_rate}. Using default.")

            logger.info("Coqui TTS engine initialized successfully.")

        except Exception as e:
            logger.error(f"Error initializing Coqui TTS engine: {e}", exc_info=True)
            self.tts = None # Ensure it's None on failure

    def set_word_callback(self, callback: Callable[[int], Any]):
        """
        Set callback function for word synchronization.

        Args:
            callback: Function to call when a new word is spoken (receives word index).
        """
        self.word_callback = callback
        # Connect the Qt signal to the provided callback
        if callback:
            self.word_signal.connect(callback)
            logger.debug("Word callback connected.")

    def speak(self, text: str, word_boxes: Optional[List[Tuple[float, float, float, float]]] = None):
        """
        Speak text with word synchronization.

        Args:
            text: The text to synthesize and play.
            word_boxes: List of bounding boxes for words in the text (for highlighting).
        """
        if not self.tts:
            logger.error("TTS engine not initialized or failed to initialize.")
            return

        if not text or not text.strip():
            logger.warning("Attempted to speak empty text.")
            return

        # Stop any current playback
        self.stop()
        self.stopped = False # Reset stopped flag for new playback

        # Manage long text by chunking
        max_chunk_size = 500
        if len(text) > max_chunk_size:
            logger.info(f"Text length ({len(text)}) exceeds max chunk size ({max_chunk_size}), splitting.")
            # Simple sentence-aware-ish splitting
            import textwrap
            sentences = textwrap.wrap(text, width=max_chunk_size // 2, break_long_words=False, break_on_hyphens=False)
            chunks = []
            current_chunk = ""
            for sentence in sentences:
                # Add 1 for space
                if len(current_chunk) + len(sentence) + 1 <= max_chunk_size:
                    current_chunk += sentence + " "
                else:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence + " "
            if current_chunk.strip():
                chunks.append(current_chunk.strip())

            logger.debug(f"Text split into {len(chunks)} chunks.")
            self.text_chunks = chunks
            self.current_chunk_index = 0
            self.current_text = self.text_chunks[0] if self.text_chunks else ""
        else:
            self.current_text = text
            self.text_chunks = None
            self.current_chunk_index = -1

        self.word_boxes = word_boxes

        # Start playback process
        self.is_playing = True
        self.is_paused = False
        logger.info("Starting TTS playback process.")

        # Start preprocessing remaining chunks in background
        if self.text_chunks and len(self.text_chunks) > 1:
            self.preprocess_thread = threading.Thread(target=self._preprocess_remaining_chunks, daemon=True)
            self.preprocess_thread.start()
            logger.debug("Started background preprocessing thread.")

        # Start main playback worker
        self.playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
        self.playback_thread.start()
        logger.debug("Started main playback worker thread.")


    def _preprocess_remaining_chunks(self):
        """Preload audio for remaining chunks in parallel."""
        if not self.text_chunks or len(self.text_chunks) <= 1:
            return

        logger.debug("Preprocessing remaining chunks started.")
        for idx in range(1, len(self.text_chunks)):
            if self.stopped:
                logger.info("Preprocessing stopped due to playback stop.")
                return

            chunk_text = self.text_chunks[idx]
            if not chunk_text.strip():
                logger.debug(f"Skipping empty chunk {idx}.")
                continue

            processed_text = self._preprocess_text(chunk_text)
            try:
                logger.debug(f"Generating audio for chunk {idx}...")
                wav = self.tts.tts(processed_text)
                if wav is not None and len(wav) > 0:
                    self.audio_queue.put((wav, processed_text))
                    logger.debug(f"[Preload] Queued chunk {idx + 1}/{len(self.text_chunks)}")
                else:
                    logger.warning(f"[Preload] Generated empty audio for chunk {idx + 1}. Skipping.")
            except Exception as e:
                logger.error(f"[Preload ERROR] Failed to generate audio for chunk {idx + 1}: {e}")

    def pause(self):
        """Pause TTS playback."""
        if self.is_playing and not self.is_paused:
            self.is_paused = True
            logger.info("TTS playback paused.")

    def resume(self):
        """Resume TTS playback."""
        if self.is_playing and self.is_paused:
            self.is_paused = False
            logger.info("TTS playback resumed.")

    def stop(self):
        """Stop TTS playback."""
        if self.is_playing or self.is_paused:
            logger.info("Stopping TTS playback...")
            self.is_playing = False
            self.is_paused = False
            self.stopped = True

            # Clear the audio queue
            logger.debug("Clearing audio queue...")
            cleared_items = 0
            try:
                while True:
                    self.audio_queue.get_nowait()
                    cleared_items += 1
            except queue.Empty:
                pass
            if cleared_items > 0:
                logger.debug(f"Cleared {cleared_items} items from the queue.")

            # Attempt to stop sounddevice playback
            try:
                sd.stop()
            except Exception as e:
                logger.debug(f"Error stopping sounddevice (might not be playing): {e}")

            logger.info("TTS playback stopped.")

    def _playback_worker(self):
        """Worker thread for TTS playback."""
        logger.debug("Playback worker thread started.")
        try:
            # --- 1. Play the first/current chunk ---
            if self.current_text.strip():
                 self._process_current_chunk()
            else:
                 logger.warning("First chunk is empty, skipping initial processing.")

            # --- 2. Play chunks from the queue (preloaded or generated on-the-fly) ---
            logger.debug("Entering queue playback loop.")
            while not self.stopped:
                # Handle pause
                if self.is_paused:
                    time.sleep(0.1) # Sleep briefly while paused
                    continue

                try:
                    # Get next chunk from queue (blocks for a short time)
                    wav_data, processed_text = self.audio_queue.get(timeout=1.0)
                    logger.debug("Retrieved chunk from queue.")
                    if isinstance(wav_data, list):
                        wav_data = np.array(wav_data, dtype=np.float32)

                    word_timings = self._estimate_word_timings(processed_text, len(wav_data))
                    self._play_with_word_sync(wav_data, word_timings)

                except queue.Empty:
                    # Timeout on queue get, check if we should generate remaining chunks
                    break # Exit loop to check for remaining chunks

            # --- 3. If chunks remain and weren't preloaded, generate and play them ---
            if self.text_chunks and self.current_chunk_index < len(self.text_chunks) - 1:
                logger.debug("Processing remaining chunks sequentially.")
                while (not self.stopped and
                       self.current_chunk_index < len(self.text_chunks) - 1):
                    if self.is_paused:
                        time.sleep(0.1)
                        continue

                    self.current_chunk_index += 1
                    self.current_text = self.text_chunks[self.current_chunk_index]
                    logger.info(f"Processing chunk {self.current_chunk_index + 1}/{len(self.text_chunks)} sequentially.")
                    self._process_current_chunk() # This plays it immediately

            logger.info("Playback worker finished its loop.")

        except Exception as e:
            logger.error(f"TTS playback worker error: {e}", exc_info=True)
        finally:
            # Ensure state is reset when worker finishes
            self.is_playing = False
            self.is_paused = False
            # self.stopped might remain True if stopped intentionally
            logger.debug("Playback worker thread finished.")


    def _process_current_chunk(self):
        """Process and play the current text chunk."""
        if not self.current_text.strip():
            logger.debug("Skipping processing of empty chunk.")
            return

        if not self.tts:
             logger.error("TTS engine unavailable during chunk processing.")
             return

        processed_text = self._preprocess_text(self.current_text)
        logger.debug(f"[TTS] Generating audio for chunk {self.current_chunk_index + 1}/{len(self.text_chunks) if self.text_chunks else 1}: '{processed_text[:50]}...'")

        try:
            # --- Generate Audio ---
            wav = self.tts.tts(processed_text)
            if wav is None or len(wav) == 0:
                logger.warning("[TTS WARNING] Generated audio is empty for chunk. Skipping.")
                return

            if isinstance(wav, list):
                wav = np.array(wav, dtype=np.float32)

            logger.debug(f"Audio generated, length: {len(wav)} samples.")

            # --- Estimate Timings & Play ---
            word_timings = self._estimate_word_timings(processed_text, len(wav))
            logger.debug(f"Estimated {len(word_timings)} word timings.")
            self._play_with_word_sync(wav, word_timings)
            logger.debug("Finished playing current chunk.")

        except Exception as e:
            logger.error(f"[TTS ERROR] Failed to process chunk {self.current_chunk_index + 1}: {e}", exc_info=True)


    def _estimate_word_timings(self, text: str, audio_length_samples: int) -> List[float]:
        """
        Estimate word timings based on text and audio length.

        Args:
            text: The processed text.
            audio_length_samples: Length of the audio in samples.

        Returns:
            List of estimated start times (in seconds) for each word.
        """
        words = text.split()
        if not words:
            return []

        sample_rate = 22050 # Assumed sample rate used by Coqui TTS
        audio_duration_seconds = audio_length_samples / sample_rate

        total_chars = sum(len(word) for word in words)
        if total_chars == 0:
             # Avoid division by zero
             return [0.0] * len(words)

        # Estimate time per character
        time_per_char = audio_duration_seconds / total_chars

        # Calculate word timings with a small gap
        word_timings = []
        current_time = 0.0
        for word in words:
            word_timings.append(current_time)
            # Time for this word + small gap
            current_time += len(word) * time_per_char + 0.05

        # Ensure timings don't exceed audio duration
        # Adjust if necessary (simple linear scaling might be better for precision)
        if word_timings and current_time > audio_duration_seconds:
             logger.debug("Estimated timings slightly exceed audio duration, normalizing.")
             # Simple scaling to fit within duration (keeps relative spacing)
             if current_time > 0:
                scale_factor = audio_duration_seconds / current_time
                word_timings = [t * scale_factor for t in word_timings]

        return word_timings


    def _play_with_word_sync(self, wav: np.ndarray, word_timings: List[float]):
        """
        Play audio data and emit word signals synchronized with estimated timings.

        Args:
            wav: The audio data as a NumPy array.
            word_timings: List of start times (seconds) for each word.
        """
        if self.stopped or not self.is_playing:
            return

        if len(wav) == 0:
            logger.error("Cannot play empty audio data.")
            return

        sample_rate = 22050 # Standard assumed rate for Coqui TTS models

        try:
            logger.debug(f"Starting playback: {len(wav)} samples at {sample_rate}Hz (~{len(wav)/sample_rate:.2f}s)")
            sd.play(wav, samplerate=sample_rate)
            logger.debug("Audio playback initiated.")

            # --- Word Synchronization Loop ---
            start_time = time.time()
            current_word_index = 0
            audio_duration = len(wav) / sample_rate

            while (current_word_index < len(word_timings) and
                   not self.stopped and
                   not self.is_paused):

                elapsed_time = time.time() - start_time

                # Check if it's time for the next word
                if elapsed_time >= word_timings[current_word_index]:
                    logger.debug(f"Emitting word signal for word index {current_word_index}")
                    self.word_signal.emit(current_word_index)
                    current_word_index += 1

                # Brief sleep to prevent busy-waiting
                time.sleep(0.01)

                # Safety check to prevent infinite loop if timing is off
                if elapsed_time > audio_duration + 1.0: # 1s grace period
                    logger.warning("Playback sync loop exceeded expected audio duration + grace period. Breaking.")
                    break

            # --- Wait for Playback Completion (if not stopped/paused) ---
            if not self.stopped and not self.is_paused:
                 logger.debug("Waiting for audio playback to finish...")
                 sd.wait() # This is the correct way to wait for completion
                 logger.debug("Audio playback finished.")

            # --- Handle Stop/Pause during sync ---
            if self.stopped or self.is_paused:
                logger.debug("Stopping audio playback due to stop/pause command.")
                sd.stop() # Stop playback immediately

        except Exception as e:
            logger.error(f"Error during audio playback or synchronization: {e}", exc_info=True)
            try:
                sd.stop()
            except:
                pass # Ignore errors stopping if the main error was playing


    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text to remove special characters and fix abbreviations for better TTS.

        Args:
            text: The raw text.

        Returns:
            The preprocessed text.
        """
        if not text:
            return ""

        # 1. Expand common acronyms/abbreviations (e.g., GPT -> G P T)
        text = self._expand_abbreviations(text)

        # 2. Replace or remove problematic characters/symbols
        replacements = {
            '\uf0b7': '-',      # Bullet point symbol
            '—': '-',           # Em dash
            '–': '-',           # En dash
            '->': 'to',         # Arrow
            '→': 'to',
            '/': ' ',           # Slash
            '+': ' plus ',      # Plus sign
            'ﬂ': 'fl',          # Ligature fi
            'ﬁ': 'fi',          # Ligature fl
            'ﬀ': 'ff',
            'ﬃ': 'ffi',
            'ﬄ': 'ffl',
            '\u2013': '-',      # En dash
            '\u2014': '-',      # Em dash
            '\u2018': "'",      # Left single quotation mark
            '\u2019': "'",      # Right single quotation mark
            '\u201c': '"',      # Left double quotation mark
            '\u201d': '"',      # Right double quotation mark
            # Add more as needed based on your documents
        }
        for char, repl in replacements.items():
            text = text.replace(char, repl)

        # 3. Remove non-ASCII characters (optional, can be lossy)
        # text = ''.join(c if ord(c) < 128 else ' ' for c in text)

        # 4. Normalize whitespace
        text = ' '.join(text.split())

        return text

    def _expand_abbreviations(self, text: str) -> str:
        """Expand acronyms like GPT -> G P T"""
        import re
        # Matches 2-6 consecutive uppercase letters (adjust range as needed)
        # Uses a lambda to insert spaces between letters
        return re.sub(r'\b([A-Z]{2,6})\b', lambda m: ' '.join(m.group(1)), text)

    def cleanup(self):
        """Clean up resources (alias for stop)."""
        logger.info("Cleaning up CoquiTTS resources.")
        self.stop()
        # Note: TTS model itself doesn't have an explicit cleanup in the API shown.
        # Threading resources are daemon threads and will be cleaned up when main thread exits.
        # sounddevice resources are managed by the library.