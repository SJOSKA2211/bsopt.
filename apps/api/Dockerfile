# Stage 1: builder — installs uv + deps ─────────────────────────────────
FROM python:3.14.4-slim AS builder
WORKDIR /build
 
# Install uv inside builder
RUN pip install uv
 
# Install system build deps (needed for some Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev libssl-dev curl && rm -rf /var/lib/apt/lists/*
 
# CRITICAL: lock file + requirements BEFORE src — cached layer
COPY uv.lock pyproject.toml .
COPY requirements.txt requirements-dev.txt .
RUN uv sync --no-dev --python 3.14.4
 
# Install Playwright inside builder (large, cached separately)
RUN uv run playwright install chromium --with-deps
 
# Stage 2: runtime — minimal image ─────────────────────────────────────
FROM python:3.14.4-slim AS runtime
 
# Runtime system deps for Playwright + curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libexpat1 libxcb1 libxkbcommon0 \
    libx11-6 libxcomposite1 libxdamage1 libxext6 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2 libxshmfence1 curl \
    && rm -rf /var/lib/apt/lists/*
 
# Copy venv from builder
COPY --from=builder /build/.venv /app/.venv
COPY --from=builder /root/.cache/ms-playwright /root/.cache/ms-playwright
 
# Non-root user — never run as root in production
RUN groupadd -r app && useradd -r -g app -m app
WORKDIR /app
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY data/ ./data/
RUN chown -R app:app /app
USER app
 
# Activate venv for all subsequent commands
ENV PATH="/app/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/.venv"
 
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
