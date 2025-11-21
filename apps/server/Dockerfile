FROM python:3.11-slim AS base

ENV POETRY_VERSION=1.8.3 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# System deps for scientific/python tooling
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libgl1 tesseract-ocr && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry + deps
COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}" && \
    poetry install --only main --with vision --no-root

# Copy application code
COPY . /app

EXPOSE ${PORT}

CMD ["sh", "-c", "poetry run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]

