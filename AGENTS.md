# Agent Guidelines for Scribe

## Build/Lint/Test Commands

### Development Server
- Start: `./start.sh` (recommended) or `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Database migrations: `uv run alembic upgrade head`

### Testing
- All tests: `uv run pytest`
- Single test: `uv run pytest tests/test_file.py::test_function_name`
- Example: `uv run pytest tests/test_auth.py::test_register_user`

### Code Quality
- Lint: `uv run ruff check`
- Format: `uv run ruff format`
- Type check: `uv run mypy`
- Pre-commit hooks run all quality checks automatically

## Code Style Guidelines

### Python Backend (FastAPI + SQLModel)
- **Python version**: 3.12+
- **Type hints**: Required for all functions, use modern syntax (`list[str]` not `List[str]`)
- **Imports**: Standard library → third-party → local, grouped with blank lines
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Docstrings**: Google-style for all public functions with Args/Returns/Raises
- **Line length**: 88 characters (Ruff/Black default)
- **Error handling**: Use custom exceptions from `app.utils.exceptions`
- **Database**: SQLModel for models, async context managers for sessions

### Frontend (HTMX + Alpine.js + Tailwind)
- **Framework**: HTMX for AJAX, Alpine.js for reactive components
- **Styling**: Tailwind CSS with custom color palette
- **Templates**: Jinja2 with consistent component structure
- **JavaScript**: Vanilla JS in static files, Alpine.js for interactivity
- **Naming**: kebab-case for CSS classes, camelCase for Alpine data

### Architecture Patterns
- **API routes**: RESTful endpoints in `app/api/routes/`
- **Business logic**: Service layer in `app/services/`
- **Data models**: Pydantic schemas in `app/schemas/`
- **Database models**: SQLModel in `app/models/`
- **Background tasks**: APScheduler in `app/tasks/`
- **Utilities**: Helper functions in `app/utils/`

### Security & Best Practices
- JWT authentication with configurable expiration
- Password hashing with bcrypt
- Input validation via Pydantic schemas
- CORS configured (restrict in production)
- No secrets in code (use environment variables)
- Type safety with MyPy strict mode

This is a voice note application with AI transcription, semantic search, and RAG querying.</content>
<parameter name="filePath">/Users/daniel/Documents/scribe/AGENTS.md
