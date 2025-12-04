# --- Base Python Image ---
FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files + enable buffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Working directory inside container
WORKDIR /app

# Install system dependencies required for:
# - chromadb
# - sentence-transformers
# - uvicorn performance
# - PDF handling (optional)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    wget \
    curl \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker build caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend app source
COPY app ./app

# Expose FastAPI port
EXPOSE 8000

# Optional: Healthcheck (works with ECS, Docker, Kubernetes)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run backend API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
