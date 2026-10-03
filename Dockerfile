# Use standard official Python slim image
FROM python:3.12-slim

# Set environment variables for clean container execution
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Set working directory inside container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy packaging configuration and install dependencies
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install the package and dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Create a non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose the API port
EXPOSE 8000

# Health check to monitor container status
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the FastAPI application with Uvicorn
CMD ["uvicorn", "src.api_server:app", "--host", "0.0.0.0", "--port", "8000"]
