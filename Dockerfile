FROM python:3.11-slim

# Install system dependencies including FFmpeg for OPUS/OGG WhatsApp audio
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definition
COPY requirements.txt .

# Install python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Create persistent storage directories
RUN mkdir -p data static/images/generated static/audio

# Expose server port
EXPOSE 8000

# Set environment
ENV PORT=8000
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

# Start Project AURA server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
