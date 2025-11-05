FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get remove -y build-essential gcc && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
COPY backend/ .
ENV PORT=8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
