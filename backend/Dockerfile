FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code into 'backend' directory to support absolute imports
# When context is ./backend, this creates /app/backend/...
COPY . backend/

# Set PYTHONPATH to include the current directory so 'backend' is found as a package
ENV PYTHONPATH=/app

# Run application using the backend.server module
# This ensures that 'from backend.config import Config' works correctly
CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8000"]

# Made with Bob
