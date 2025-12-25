# Scribe

A self-hosted, multi-tenant voice note application that captures voice recordings, transcribes them using local AI, and provides semantic search and RAG-based querying.

## Features

- **Voice Upload & Transcription**: Accept audio files, transcribe using MLX-Whisper (large-v3)
- **Multi-Tenant Auth**: JWT-based authentication with user-specific settings
- **Siri Integration**: Generate long-lived tokens for Siri shortcut integration
- **AI Processing**: Auto-summarization, smart tagging, and vector embedding generation
- **Semantic Search**: Vector-based note discovery using sqlite-vec
- **Vector Search**: Semantic similarity search over notes using sqlite-vec
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

### One-line startup (recommended)

```bash
./start.sh
```

This script will:
- Check that [uv](https://github.com/astral-sh/uv) is installed
- Ensure Python 3.12+ is available (uv will download if needed)
- Create `.env` from `.env.example` with a generated secret key
- Run database migrations
- Start the production server on http://localhost:8000

### Auto-start on boot/login (macOS)

1. Open **Automator** → File → New → **Application**
2. Add **Run Shell Script** action
3. Paste: `/path/to/scribe/start.sh`
4. Save as "Scribe.app"
5. Add to **System Settings** → **General** → **Login Items**

### Manual setup (if needed)

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
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

5. **Open API docs:**
   Navigate to http://localhost:8000/docs

## API Endpoints

### Authentication
- `POST /api/auth/register` - Create new user
- `POST /api/auth/login` - Get JWT token
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/api-token` - Generate long-lived API token
- `DELETE /api/auth/api-token` - Revoke current API token

### Notes
- `POST /api/upload` - Upload voice note (multipart/form-data)
- `GET /api/notes` - List all notes
- `GET /api/notes/{id}` - Get single note
- `PATCH /api/notes/{id}` - Update note
- `DELETE /api/notes/{id}` - Delete note
- `GET /api/notes/{id}/similar` - Get similar notes

### Search
- `POST /api/search` - Semantic search over notes

### Settings
- `GET /api/settings` - Get user settings
- `PATCH /api/settings` - Update settings
- `GET /api/settings/models` - List available Ollama models

### Events
- `GET /api/events` - Server-Sent Events endpoint for real-time updates

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
