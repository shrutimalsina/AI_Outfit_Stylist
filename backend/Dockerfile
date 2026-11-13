FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements-runtime.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.8.0
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY backend backend
COPY pipeline pipeline
COPY config config
COPY scripts scripts
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
