# ⚙️ Lightweight base image (Debian slim)
FROM python:3.11-slim

# Prevents Python output buffering
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# 🧩 Install only required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# 🧠 Copy only backend dependencies (not frontend or .venv)
COPY backend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# 🧩 Copy backend code only
COPY backend /app/backend

# Expose the backend port
EXPOSE 8000

# 🚀 Run FastAPI
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
