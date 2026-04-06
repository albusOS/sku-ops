FROM python:3.13-slim-bookworm AS builder

WORKDIR /build

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /usr/local/bin/uv

COPY backend/pyproject.toml backend/uv.lock ./backend/
RUN uv sync --frozen --no-dev --no-editable --directory backend


FROM python:3.13-slim-bookworm AS runtime

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        tesseract-ocr \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid 1001 --no-create-home --shell /sbin/nologin appuser

COPY --from=builder /build/backend/.venv /app/.venv

COPY backend/ .

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TIKTOKEN_CACHE_DIR="/app/.tiktoken"

RUN python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://localhost:' + os.environ.get('PORT','8000') + '/api/beta/shared/health')" || exit 1

CMD ["sh", "-c", "gunicorn main:app --bind 0.0.0.0:${PORT:-8000} --workers ${WORKERS:-1} --worker-class uvicorn.workers.UvicornWorker --worker-tmp-dir /dev/shm --timeout 120 --graceful-timeout 30 --keep-alive 5 --access-logfile -"]
