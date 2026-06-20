# ============================================================
# SmartTaxi — Dockerfile
# ============================================================

FROM python:3.12-slim

# Muhit o'zgaruvchilari
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Tizim kutubxonalari (psycopg2 uchun)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python kutubxonalari
COPY requirements.txt .
RUN pip install -r requirements.txt

# Loyiha kodlari
COPY . .

# Log papkasi
RUN mkdir -p /var/log/smarttaxi

# Port
EXPOSE 8000

# Ishga tushirish (docker-compose.yml da override qilinadi)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]