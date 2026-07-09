FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies (added netcat-traditional for entrypoint.sh)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    netcat-traditional \
    build-essential \
    libpq-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Create directories (entrypoint.sh will populate staticfiles)
RUN mkdir -p staticfiles .cache/huggingface

# Copy entrypoint script
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8000

# Use entrypoint.sh instead of direct gunicorn command
ENTRYPOINT ["./entrypoint.sh"]
