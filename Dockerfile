# syntax=docker/dockerfile:1

# Stage 1: Builder (install dependencies via uv)
FROM python:3.12-slim-bookworm AS builder

# Install system dependencies required for building some python packages or git operations
# We need git for dvc/git operations later, but maybe not strictly for building wheels unless from source.
# However, we'll install basic build tools just in case.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Create virtual environment and install dependencies
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app
COPY pyproject.toml .
# We use --no-root because we just want to install dependencies first to cache them
RUN uv venv && uv pip install -r pyproject.toml

# Stage 2: Runtime
FROM python:3.12-slim-bookworm

# Install runtime system dependencies: git is crucial for this add-on.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
COPY --from=builder /app/.venv /app/.venv

WORKDIR /app

# Copy application code
COPY app ./app

# Expose port (FastAPI default)
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
