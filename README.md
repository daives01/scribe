# Scribe

A self-hosted, multi-tenant voice note application that captures voice recordings, transcribes them using local AI, and provides semantic search and RAG-based querying.

## Features

- **Voice Upload & Transcription**: Accept audio files, transcribe using MLX-Whisper (large-v3)
- **Multi-Tenant Auth**: JWT-based authentication with user-specific settings
- **Siri Integration**: Generate long-lived tokens for Siri shortcut integration
- **AI Processing**: Auto-summarization, smart tagging, and vector embedding generation
- **Semantic Search**: Vector-based note discovery using sqlite-vec
- **RAG System**: Question-answering over personal notes using local LLM
- **CRUD Operations**: Full note management with automatic re-embedding on edits
- **Similar Notes**: KNN-based "related notes" discovery
- **Extensible LLM Config**: Per-user Ollama settings (URL, model selection)

## Prerequisites


- Python 3.12+
- [uv](https://github.com/astral-sh/uv) for dependency management
- [Ollama](https://ollama.ai/) running locally with:
  - `llama3` (or your preferred model)
  - `nomic-embed-text` for embeddings

## Quick Start

1. **Clone and setup:**
   ```bash
   cd voice-notes
   cp .env.example .env
   # Edit .env with your secret key
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Initialize database:**
   ```bash
   uv run alembic upgrade head
   ```

4. **Start the server:**
   ```bash
   uv run fastapi dev app/main.py
   ```

5. **Open API docs:**
   Navigate to http://localhost:8000/docs

## API Endpoints

### Authentication
- `POST /auth/register` - Create new user
- `POST /auth/login` - Get JWT token
- `GET /auth/me` - Get current user info
- `POST /auth/api-token` - Generate long-lived API token
- `DELETE /auth/api-token` - Revoke current API token

### Notes
- `POST /upload` - Upload voice note (multipart/form-data)
- `GET /notes` - List all notes
- `GET /notes/{id}` - Get single note
- `PATCH /notes/{id}` - Update note
- `DELETE /notes/{id}` - Delete note
- `GET /notes/{id}/similar` - Get similar notes

### Search & RAG
- `POST /search` - Semantic search
- `POST /ask` - RAG-based Q&A

### Settings
- `GET /settings` - Get user settings
- `PATCH /settings` - Update settings
- `GET /settings/models` - List available Ollama models

### Health
- `GET /health` - System health check

## Development

Run tests:
```bash
uv run pytest
```

Run migrations:
```bash
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

## Architecture

```
app/
├── main.py              # FastAPI app initialization
├── config.py            # Settings (Pydantic BaseSettings)
├── database.py          # SQLModel engine, session management
├── models/              # SQLModel database models
├── schemas/             # Pydantic request/response schemas
├── api/routes/          # API endpoint handlers
├── services/            # Business logic layer
├── tasks/               # Background task processors
└── utils/               # Helper utilities
```

## License

MIT
