FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.11.29 /uv /uvx /bin/

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

COPY gateway_provider.py main.py ./
COPY kira ./kira

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "kira.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
