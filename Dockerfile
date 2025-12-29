# Multi-stage Dockerfile for Oxide LLM Orchestrator
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY src/oxide/web/frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY src/oxide/web/frontend/ ./

# Build frontend
RUN npm run build

# Python backend stage
FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY config/ ./config/

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy frontend build from previous stage
COPY --from=frontend-builder /app/frontend/dist ./src/oxide/web/frontend/dist

# Expose ports
EXPOSE 8000 5173

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV OXIDE_CONFIG_PATH=/app/config/default.yaml

# Run the application
CMD ["uv", "run", "oxide-all"]
