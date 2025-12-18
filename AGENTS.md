# Scribe AI Agents Documentation

Scribe is a self-hosted voice memo and transcription tool that uses local AI to transform audio into organized, searchable notes.

## Project Overview

Scribe allows users to upload audio files (voice memos, recordings, etc.) and automatically:
1.  **Transcribes** the audio into text using local models.
2.  **Analyzes** the transcript to generate summaries and tags (via LLM).
3.  **Indexes** the content for semantic search using vector embeddings.
4.  **Notifies** the user of new notes through integrations like Home Assistant.

## Tech Stack

### Backend
- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Python)
- **Database:** SQLite
- **Vector Search:** [sqlite-vec](https://github.com/asg017/sqlite-vec) (SQLite extension for vector search)
- **Task Queue:** Background tasks via FastAPI

### AI / Machine Learning
- **Transcription:** [NVIDIA NeMo Parakeet v2](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2) (State-of-the-art ASR model)
- **Embeddings:** [sentence-transformers](https://www.sbert.net/) (for semantic vector generation)
- **LLM Integration:** OpenAI-compatible API (Ollama, OpenAI, etc. for summarization and tagging)

### Frontend
- **Templating:** Jinja2
- **Interactivity:** [HTMX](https://htmx.org/)
- **Styling:** [Tailwind CSS](https://tailwindcss.com/)

### Infrastructure & Integrations
- **Containerization:** Docker & Docker Compose
- **Home Automation:** Home Assistant (HASS) via REST API for notifications

## Core Services (`app/services/`)
- `transcriber.py`: Handles audio-to-text conversion.
- `embeddings.py`: Generates vector embeddings for notes.
    - `llm.py`: Interfaces with OpenAI-compatible APIs for tagging and metadata extraction.
- `search.py`: Manages semantic search logic using `sqlite-vec`.
- `notifier.py`: Sends notifications to external services.
