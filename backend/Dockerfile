# ⚙️ Lightweight base image
FROM python:3.11-slim

# 🧩 System dependencies for PyMuPDF + Mongo + SSL
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libssl-dev libffi-dev build-essential poppler-utils \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 🧩 Copy and install dependencies separately (layer cache)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 🧩 Copy the backend code
COPY backend /app/backend

# 🔧 Environment
ENV PYTHONUNBUFFERED=1 \
    PORT=8000

# 🚀 Start FastAPI
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
