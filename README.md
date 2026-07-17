# Music RAG

Production-grade Audio RAG Data Ingestion Platform for Songs, Podcasts, and Videos.

## Getting Started

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -e ".[all]"
   ```

3. Start Qdrant (Vector Database):
   ```bash
   docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant
   ```

4. Run the application:
   ```bash
   python src/ragpipe/main.py
   ```
