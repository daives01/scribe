#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting Scribe in production mode..."

if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Install it with:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✓ uv installed"

if ! command -v ffmpeg &> /dev/null; then
    echo "❌ ffmpeg is not installed. Install it with:"
    echo "   brew install ffmpeg"
    exit 1
fi

echo "✓ ffmpeg installed"

uv python pin 3.12 || echo "✓ Python 3.12+ available"

# Set production environment
export DEBUG=false

# Ensure .env exists and has production settings
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cat > .env << EOF
DEBUG=false
SECRET_KEY=$(openssl rand -base64 32 | tr -d '=+/' | cut -c1-32)
DATABASE_URL=sqlite:///./scribe.db
BASE_URL=http://localhost:8000
CORS_ORIGINS=["*"]
EOF
fi

# Update DEBUG in .env if needed
if grep -q "^DEBUG=true" .env 2>/dev/null; then
    sed -i '' 's/^DEBUG=true/DEBUG=false/' .env
fi

# Ensure secret key is set
if grep -q "your-super-secret-key-change-in-production\|change-me-in-production" .env; then
    SECRET_KEY=$(openssl rand -base64 32 | tr -d '=+/' | cut -c1-32)
    sed -i '' "s/your-super-secret-key-change-in-production/$SECRET_KEY/" .env
    sed -i '' "s/change-me-in-production/$SECRET_KEY/" .env
fi

mkdir -p uploads logs

echo "🗄️ Running database migrations..."
uv run alembic upgrade head

echo "🚀 Starting Scribe in production mode..."

# Run with production settings: multiple workers, proper logging
exec uv run uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2 \
    --log-level info \
    --access-log \
    --no-use-colors

