FROM python:3.11-slim

WORKDIR /app

# Use Debian mirrors for faster downloads (Yandex mirror) and install system dependencies
ENV DEBIAN_FRONTEND=noninteractive
RUN set -eux; \
    sed -i 's|https\?://deb.debian.org|http://mirror.yandex.ru|g' /etc/apt/sources.list 2>/dev/null || true; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i 's|https\?://deb.debian.org|http://mirror.yandex.ru|g' /etc/apt/sources.list.d/debian.sources; \
    fi; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      gcc \
      postgresql-client; \
    rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

