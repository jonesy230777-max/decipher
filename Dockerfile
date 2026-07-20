# Multi-stage production image for Decipher.
# Stage 1: build the React dashboard.
# Stage 2: Python 3.12 + nginx + supervisord runtime with the built assets.

# -----------------------------------------------------------------------
# Stage 1: dashboard build
# -----------------------------------------------------------------------
FROM node:22-slim AS dashboard-build

WORKDIR /build
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci --prefer-offline

COPY dashboard/ .
RUN npm run build


# -----------------------------------------------------------------------
# Stage 2: runtime
# -----------------------------------------------------------------------
FROM python:3.12-slim

# System packages: nginx, supervisord, gzip (for backup script), pg_client
RUN apt-get update && apt-get install -y --no-install-recommends \
        nginx \
        supervisor \
        gzip \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY app/           ./app/
RUN apt-get update && apt-get install -y --no-install-recommends \
        libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
        libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
        libgbm1 libasound2 libpango-1.0-0 libcairo2 fonts-liberation \
    && rm -rf /var/lib/apt/lists/* \
    && playwright install chromium
COPY scripts/       ./scripts/
COPY reference_docs/ ./reference_docs/
COPY nginx/         ./nginx/
COPY supervisord/   ./supervisord/
COPY schema.sql seed.sql ./

# Dashboard static build from Stage 1
COPY --from=dashboard-build /build/dist ./dashboard/dist/

# Create runtime directories
RUN mkdir -p \
        /var/log/supervisor \
        /var/log/nginx \
        /app/var/backups \
        /app/_squarespace_exports \
    && chmod +x /app/scripts/pg_backup.sh

# nginx needs write access to /var/lib/nginx for temp files
RUN chown -R www-data:www-data /var/log/nginx

# Build-time metadata (injected by CI or docker build --build-arg)
ARG BUILD_DATE=unknown
ARG GIT_SHA=unknown
ENV BUILD_DATE=${BUILD_DATE} GIT_SHA=${GIT_SHA}

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=5s --retries=6 \
    CMD curl -sf http://127.0.0.1:8000/api/health | grep -q '"status":"ok"'

CMD ["/usr/bin/supervisord", "-c", "/app/supervisord/supervisord.conf"]
