# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 — build the React app
# ---------------------------------------------------------------------------
FROM node:22-alpine AS web

WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


# ---------------------------------------------------------------------------
# Stage 2 — runtime: one Flask process serves the API and the built SPA
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    PORT=8000 \
    FRONTEND_DIST=/app/frontend/dist

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY database/ ./database/
COPY --from=web /web/dist ./frontend/dist

# Run unprivileged; `instance/` is the only path the app ever writes to
# (SQLite development mode — a managed database is used in production).
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/backend/instance \
    && chown -R appuser:appuser /app
USER appuser

WORKDIR /app/backend
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/api/v1/health" || exit 1

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY:-2} --threads 4 --timeout 60 --access-logfile - --error-logfile - wsgi:app"]
