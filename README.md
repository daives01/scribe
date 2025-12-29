# Scribe

A self-hosted voice note application with AI transcription and semantic search. Record voice notes, get them transcribed locally, and search through them using natural language.
**Platform Note**: This app uses MLX-Whisper, which is optimized for Apple Silicon Macs (uses Metal for GPU acceleration). While MLX-Whisper can run on Linux, it will be CPU-only and significantly slower. For Linux deployments, consider switching to `faster-whisper` in `app/services/transcription_service.py` for better performance with CUDA/ROCm support.

## What It Does

- Record and upload voice notes
- Transcribe audio using local MLX-Whisper
- Search notes semantically using vector embeddings
- Auto-generate summaries and tags with Ollama
- Multi-user support with JWT authentication

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) - `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [ffmpeg](https://ffmpeg.org/) - `brew install ffmpeg` (macOS)
- [Ollama](https://ollama.ai/) running locally with:
  - A chat model (e.g., `llama3`, `qwen3:4b-instruct`)
  - `nomic-embed-text` for embeddings

## Running the Application

### Development Mode

```bash
./start.sh
```

Starts the server in development mode on http://localhost:8000

### Production Mode

```bash
./start-production.sh
```

Starts the server with:
- Multiple workers (2)
- Production logging
- `DEBUG=false`
- Auto-creates `.env` with secure defaults

### Auto-Start on macOS

1. Open **Automator** → File → New → **Application**
2. Add **Run Shell Script** action
3. Paste: `/Users/ives/Documents/scribe/start-production.sh`
4. Save as "Scribe.app"
5. Add to **System Settings** → **General** → **Login Items**

The app will start automatically on login and restart if it crashes.

## API

Full API documentation available at http://localhost:8000/docs when running.

Key endpoints:
- `POST /api/upload` - Upload voice note
- `GET /api/notes` - List notes
- `POST /api/search` - Semantic search
- `GET /health` - Health check

## Development

```bash
# Run tests
uv run pytest

# Create migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Lint & format
uv run ruff check
uv run ruff format
```

