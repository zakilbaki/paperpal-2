# Use lightweight Python image
FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/app ./app

# Expose port for Render
ENV PORT=10000
ENV PYTHONUNBUFFERED=1

# Start FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
