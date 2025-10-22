FROM python:3.11-slim

# 🧩 Install SSL certificates and basic tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 🧩 Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt certifi

# 🧩 Copy project files
COPY . .

ENV PYTHONUNBUFFERED=1

# 🧠 Start FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
