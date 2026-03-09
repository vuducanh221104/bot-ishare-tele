# Isharetech-bot Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create volume for persistent data
VOLUME ["/app/data"]

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["python", "-u", "bot.py"]
