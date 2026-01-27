# Python base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Scrapy, lxml, psycopg2, etc.
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    libssl-dev \
    zlib1g-dev \
    libjpeg-dev \
    curl \
    netcat-openbsd \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy docker scripts
COPY docker/entrypoint.sh /app/docker/entrypoint.sh
COPY docker/start-cron.sh /app/docker/start-cron.sh
COPY docker/cron-wrapper.sh /app/docker/cron-wrapper.sh
COPY docker/crontab /app/docker/crontab
RUN chmod +x /app/docker/entrypoint.sh /app/docker/start-cron.sh /app/docker/cron-wrapper.sh

# Copy application code
COPY src/ /app/src/
COPY .env /app/.env

# Set Python path
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Create logs directory
RUN mkdir -p /app/logs /app/data

# Default command (can be overridden)
CMD ["python", "src/manage.py", "check"]
