#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting Scribe..."

if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Install it with:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✓ uv installed"

uv python pin 3.12 || echo "✓ Python 3.12+ available"

if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
fi

if grep -q "your-super-secret-key-change-in-production" .env; then
    echo "🔑 Generating new SECRET_KEY..."
    SECRET_KEY=$(openssl rand -base64 32 | tr -d '=+/' | cut -c1-32)
    sed -i '' "s/your-super-secret-key-change-in-production/$SECRET_KEY/" .env
    echo "✓ Secret key updated in .env"
fi

mkdir -p uploads

echo "🗄️ Running database migrations..."
uv run alembic upgrade head

echo "🎤 Starting Scribe on http://localhost:8000..."
echo "   API docs: http://localhost:8000/docs"
echo "   Web UI:   http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop"

exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
