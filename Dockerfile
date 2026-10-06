FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Dependencies first so this layer is cached until the lockfile changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

# Data directory is a volume so the cache survives container restarts.
ENV PATH="/app/.venv/bin:$PATH" CACHE_DATABASE_URL=sqlite:////data/cache.db
RUN useradd --system app && mkdir /data && chown app /data
USER app
VOLUME /data

EXPOSE 8000
CMD ["uvicorn", "cache_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
