# RAKSHA AI - Production Dockerfile optimized for Render
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY backend/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy project files
COPY . /app

# Copy frontend to backend static directory
COPY frontend/index.html /app/backend/index.html
COPY frontend/app.js /app/backend/app.js
COPY frontend/styles.css /app/backend/styles.css
COPY frontend/dashboard_enhancements.css /app/backend/dashboard_enhancements.css
COPY frontend/sw.js /app/backend/sw.js
COPY frontend/manifest.json /app/backend/manifest.json
COPY frontend/auth.html /app/backend/auth.html

# Create data directory for SQLite
RUN mkdir -p /app/backend/data

# Set environment variables for production
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Set working directory to backend
WORKDIR /app/backend

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]