FROM ghcr.io/astral-sh/uv:0.8.22 AS uv
FROM python:3.11-slim
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_PROJECT_ENVIRONMENT=/opt/stylist-venv
ENV PATH="/opt/stylist-venv/bin:$PATH"
COPY backend/pyproject.toml backend/uv.lock backend/
RUN uv sync --project backend --locked --no-dev --extra app --extra ml
COPY backend backend
COPY pipeline pipeline
COPY config config
COPY scripts scripts
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
