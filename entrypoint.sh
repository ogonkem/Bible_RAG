#!/bin/bash
set -e

# Use default values if environment variables not set
DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}

echo "================================"
echo "Bible RAG Startup"
echo "================================"
echo "Database: $DB_HOST:$DB_PORT"
echo ""

# Wait for PostgreSQL with timeout
echo "Waiting for PostgreSQL on $DB_HOST:$DB_PORT..."
timeout 30 bash -c "until nc -z $DB_HOST $DB_PORT 2>/dev/null; do sleep 1; done" || {
    echo "❌ PostgreSQL failed to start within 30 seconds!"
    echo "   Check if database container is running: docker-compose ps"
    echo "   Check database logs: docker-compose logs db"
    exit 1
}
echo "✅ PostgreSQL is ready"
echo ""

# Run migrations
echo "Running Django migrations..."
if ! python manage.py migrate --noinput; then
    echo "❌ Migrations failed!"
    echo "   Check logs above for details"
    exit 1
fi
echo "✅ Migrations complete"
echo ""

# Collect static files (non-fatal if fails)
echo "Collecting static files..."
if python manage.py collectstatic --noinput --clear 2>/dev/null; then
    echo "✅ Static files collected"
else
    echo "⚠️  Static files collection had issues (continuing anyway)"
fi
echo ""

# Create cache directory for HuggingFace models
mkdir -p /app/.cache/huggingface
echo "✅ HuggingFace cache directory ready"
echo ""

# Start Gunicorn
echo "Starting Gunicorn on 0.0.0.0:8000..."
echo "================================"
echo ""
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class sync \
    --timeout 300 \
    --access-logfile - \
    --error-logfile - \
    --log-level info