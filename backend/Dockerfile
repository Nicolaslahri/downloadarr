FROM python:3.12-slim AS base

# Enable Debian non-free for unrar (it's not in main).
RUN echo "deb http://deb.debian.org/debian bookworm main contrib non-free non-free-firmware" \
        > /etc/apt/sources.list.d/non-free.list \
    && apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        curl \
        par2 \
        p7zip-full \
        unrar \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first for better build caching
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir -e ".[torrents]" || pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
