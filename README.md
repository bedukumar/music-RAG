# Music RAG (RagPipe)

Production-grade Audio Retrieval-Augmented Generation (RAG) Data Ingestion Platform designed specifically for audio content like Songs, Podcasts, and Videos.

RagPipe processes audio files, extracts embeddings using advanced audio models (like CLAP or Sentence Transformers), and stores them alongside rich metadata in a local relational database and a high-performance vector database, enabling semantic search and retrieval over audio data.

## Features

- **Audio Processing & Embedding**: Leverages libraries like `librosa` and `soundfile` to process audio, and models like `sentence-transformers` and `laion-clap` to generate robust vector embeddings.
- **Relational & Vector Storage**: Utilizes `SQLAlchemy` (SQLite) for storing metadata (e.g., `ragpipe.db`) and `Qdrant` for scalable vector similarity search.
- **Async API**: Built with `FastAPI` and `uvicorn` for high-performance, asynchronous endpoints for data ingestion and querying.
- **Local Visualization**: Designed to support tools that visualize vector embeddings and their associated metadata directly from local storage.
- **Observability**: Integrated with `structlog` and `prometheus-client` for monitoring and logging.

## Prerequisites

- Python 3.11+
- Docker (for running Qdrant locally)
- System audio dependencies (e.g., `ffmpeg` if required by underlying audio libraries)

## Installation

1. **Set up a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

2. **Install the dependencies:**
   Install the project along with all optional dependencies for development and audio processing:
   ```bash
   pip install -e ".[all]"
   ```

3. **Environment Variables:**
   Copy the example environment file and update it with your settings:
   ```bash
   cp .env.example .env
   ```
   *(Note: The `.env` file is ignored by git to protect sensitive information).*

## Getting Started

1. **Start Qdrant (Vector Database):**
   ```bash
   docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant
   ```

2. **Run the Application:**
   You can start the main API server using the command-line script:
   ```bash
   ragpipe
   ```
   Or explicitly via Python:
   ```bash
   python src/ragpipe/main.py
   ```

## Development and Testing

- **Run tests:**
  ```bash
  pytest
  ```
- **Linting & Formatting:**
  The project uses `ruff` and `mypy` for code quality:
  ```bash
  ruff check src tests
  mypy src
  ```

## License

This project is licensed under the MIT License.
