# ⚙️ Use slim Python image (lightweight and fast)
FROM python:3.11-slim

# 🧩 Install minimal system dependencies for PyMuPDF and Mongo
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libssl-dev \
    libffi-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 🧩 Install backend dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 🧩 Copy only backend code (avoid full repo)
COPY backend /app/backend

# 🔧 Environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=8000

# 🚀 Launch FastAPI backend
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
