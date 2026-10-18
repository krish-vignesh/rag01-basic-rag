
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /bin/

WORKDIR /app

# Create the non-root application user first.
RUN useradd --create-home --shell /usr/sbin/nologin appuser

# Install dependencies while keeping the environment owned by root.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

# Copy only application source with the correct ownership.
COPY --chown=appuser:appuser src/ ./src/

# Run the API as a non-root user.
USER appuser

CMD ["/app/.venv/bin/uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
