FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY config.py .
COPY elasticsearch_client.py .
COPY snowflake_client.py .
COPY main.py .

# Make main.py executable
RUN chmod +x main.py

# Create directory for configuration files
RUN mkdir -p /config

# Set environment variables (can be overridden at runtime)
ENV LOG_LEVEL=INFO
ENV BATCH_SIZE=1000
ENV SYNC_INTERVAL=300

# Run the application
ENTRYPOINT ["python", "main.py"]
CMD []
