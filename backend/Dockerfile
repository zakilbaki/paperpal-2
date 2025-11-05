# 🐍 Use lightweight base image
FROM python:3.11-slim

# Prevent Python buffering
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy only requirements first (for layer caching)
COPY backend/requirements.txt .

# Install system deps and Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev \
 && pip install --no-cache-dir -r requirements.txt \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy the backend code only
COPY backend/ .

# Expose port and start FastAPI
ENV PORT=8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
