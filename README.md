# SpokenSense: A Smart Offline PDF Reader with Voice Playback and Local AI Chat Assistant

## Overview

SpokenSense is a privacy-focused, offline-capable, intelligent PDF reader built for researchers, students, and knowledge workers who wish to consume academic documents more efficiently through voice playback and AI-powered conversations.

The application is intended to be a personal productivity tool that allows users to read, listen to, and query PDF documents in real-time using only local resources. It is fully offline, with no external API calls or data transfers, ensuring complete privacy.

## Features

- **PDF Viewing and Navigation**: Multi-tab interface for managing multiple documents
- **Word-level Synchronized Text-to-Speech (TTS)**: High-quality voice playback with word highlighting
- **Offline Local LLM-based Question Answering**: Ask questions about your documents using RAG
- **Smart Highlight and Voice Control**: Words are highlighted as they are read aloud
- **Multi-tab PDF Management**: Work with multiple documents simultaneously
- **Persistent Memory**: Automatically resume from last page

## Architecture

### Core Functional Modules

#### 1. PDF Processing System

- **Goal**: Efficiently extract text with structure and word-level positions from PDFs for both highlighting and AI context
- **Libraries Used**:
  - PyMuPDF (primary) – for fast and precise text + bounding box extraction
  - pdfplumber (fallback) – used only if PyMuPDF fails
- **Features**:
  - Word-level bounding boxes for real-time TTS highlighting
  - Page-by-page processing with LRU-style caching
  - Dual engine design for robustness (PyMuPDF + pdfplumber)
  - Configurable chunk sizes for AI processing
  - MD5-based file hashing for persistent caching and file tracking

#### 2. Text-to-Speech Engine

- **Goal**: Provide high-quality offline voice playback with word synchronization and playback controls
- **Library Used**:
  - TTS by Coqui (https://github.com/coqui-ai/TTS)
- **Features**:
  - High-quality realistic voice synthesis
  - Custom threading wrapper for pause/resume/stop controls
  - Word-level callback synchronization (optional, based on timing estimates)
  - User-configurable voice selection, speech rate, and volume
  - Preload or stream audio playback using sounddevice
  - Answer-readback from AI assistant via TTS

#### 3. AI Chat Assistant with RAG

- **Goal**: Enable users to ask natural-language questions about the PDF content offline using local LLMs
- **Libraries Used**:
  - sentence-transformers (for chunk embeddings)
  - ChromaDB (as persistent local vector database)
  - Ollama (for serving local LLMs such as Mistral, Nous Hermes, Phi-3, etc.)
- **RAG Architecture**:
  - PDF content is chunked using configurable sliding window (e.g., 300 words + 50 overlap)
  - Chunks are embedded using sentence-transformers (all-MiniLM-L6-v2)
  - Embeddings stored and queried using ChromaDB
  - Retrieved chunks are passed into the QA pipeline with Ollama LLM as backend
  - LLM responds to user queries in context of current or full document
  - Optional: AI answers can be read out loud using the TTS module
- **Local LLM Options** (served via Ollama):
  - Nous Hermes 2 (Mistral) – recommended
  - OpenHermes 2.5
  - Phi-3 Mini or Medium
  - TinyLLaMA for minimal footprint
  - Models chosen based on available RAM (ideal setup: 16GB+)

#### 4. Configuration Management

- **Goal**: Centralized config system for app behavior, model settings, and directory paths
- **Libraries**:
  - Custom config.py
  - python-dotenv for .env support
- **Features**:
  - Control over TTS voice, rate, model path
  - PDF chunk size, embedding model name
  - LLM model selection, host/port
  - Paths for cache, user state, embeddings
  - Supports override via environment variables

#### 5. GUI and Interaction (PyQt5)

- **Goal**: Build a modern, responsive multi-tab interface that supports document display, highlighting, and interaction
- **Features**:
  - PyQt5-based GUI
  - QMainWindow + QTabWidget architecture
  - Integrated PDF canvas view with page rendering
  - Buttons for play, pause, stop, skip, resume
  - Tabs for multiple PDFs at once
  - Highlight words in sync with Coqui TTS playback
  - Chat panel for user queries + AI answers
  - Auto-save user state and resume from last read page
  - Scroll sync with voice playback position

## Installation

### Prerequisites

- Python 3.8 or higher
- Ollama (for local LLM serving)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/SpokenSense.git
   cd SpokenSense
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure the application:
   ```bash
   cp config/.env.example config/.env
   # Edit config/.env as needed
   ```

5. Install Ollama and download a model:
   ```bash
   # Follow instructions at https://ollama.ai/
   ollama pull nous-hermes2  # or another model of your choice
   ```

6. Run the application:
   ```bash
   python main.py
   ```

## Usage

1. Open a PDF file using File > Open PDF or Ctrl+O
2. Navigate through the document using the Previous and Next buttons
3. Use the Play, Pause, and Stop buttons to control TTS playback
4. Ask questions about the document in the chat panel
5. The application will automatically save your state and resume from where you left off

## Project Structure

```
SpokenSense/
├── main.py
├── gui/
│   ├── main_window.py
│   ├── tabs.py
│   └── highlight.py
├── pdf/
│   ├── reader.py
│   └── extractor.py
├── tts/
│   └── coqui_tts.py
├── ai/
│   ├── embedder.py
│   ├── vector_store.py
│   ├── llm_qa.py
│   └── llm_wrapper.py
├── config/
│   ├── config.py
│   └── .env
├── data/
│   ├── cache/
│   ├── embeddings/
│   └── user_state.json
├── assets/
│   └── icons/
└── README.md
```

## Dependencies

- **GUI**: PyQt5
- **PDF Parsing**: PyMuPDF, pdfplumber
- **Text-to-Speech**: Coqui TTS
- **Embedding**: SentenceTransformers (all-MiniLM-L6-v2)
- **Vector DB**: ChromaDB
- **LLM**: Ollama (Mistral, Nous Hermes, etc.)
- **Audio Playback**: sounddevice
- **Config Management**: python-dotenv

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.