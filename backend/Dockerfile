# Use a fuller Debian base to include full TLS support
FROM python:3.11-bullseye

# 🧩 Install SSL certificates and full TLS toolchain
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    openssl \
    gnutls-bin \
    curl \
 && update-ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 🧩 Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt certifi

# 🧩 Copy project files
COPY . .

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# 🧠 Start FastAPI (Render auto-exposes $PORT)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
