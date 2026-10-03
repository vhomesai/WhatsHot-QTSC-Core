# syntax=docker/dockerfile:1.7
FROM python:3.12.15-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    TRIQEE_DB_PATH=/app/data/operational.db \
    PORT=8000

WORKDIR /app

RUN groupadd --gid 10001 triqee \
    && useradd --uid 10001 --gid triqee --no-create-home --shell /usr/sbin/nologin triqee \
    && install -d -o triqee -g triqee /app/data

COPY requirements.lock pyproject.toml README.md ./
COPY src/ ./src/

# requirements.lock is the sole resolved runtime dependency set. The local
# package is installed without invoking a second dependency resolver.
RUN python -m pip install --no-cache-dir -r requirements.lock \
    && python -m pip install --no-cache-dir --no-deps . \
    && python -m compileall -q src \
    && python -c "import importlib.util; assert importlib.util.find_spec('src.api_server')"

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

ENTRYPOINT ["python", "-m", "uvicorn"]
CMD ["src.api_server:app", "--host=0.0.0.0", "--port=8000", "--workers=1", "--proxy-headers", "--forwarded-allow-ips=*", "--no-server-header"]
