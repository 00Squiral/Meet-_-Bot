FROM python:3.10-slim

# Install system dependencies, Chromium, and Chromium Driver natively
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    chromium \
    chromium-driver \
    libxi6 \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm1 \
    libglib2.0-0 \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Run the app using Gunicorn (1 worker + threads preserves background thread status)
CMD gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 8
