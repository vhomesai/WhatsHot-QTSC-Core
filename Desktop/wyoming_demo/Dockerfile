# Triqee Sovereign Appliance™ Enterprise Dockerfile (v2.5)
# Zero-Egress Air-Gapped Quantum-AI Institutional Enclave

FROM python:3.11-slim

LABEL maintainer="Triqee Labs <jon@triqee.com>"
LABEL version="2.5.0-AIRGAP-ENTERPRISE"
LABEL description="Triqee Sovereign Appliance: Air-Gapped Verification, GLI-19 Entropy & IBM QPU Bridge"

WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy microservice engine and static assets
COPY triqee_sovereign_appliance_engine.py /app/
COPY TRIQEE_SOVEREIGN_APPLIANCE_CONSOLE.html /app/

# Create data directory for persistent audit trail
RUN mkdir -p /app/data

# Set volume mount point
VOLUME ["/app/data"]

# Expose internal microservice port
EXPOSE 8088

# Health check
HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8088/api/v1/health')" || exit 1

# Run air-gapped sovereign daemon
ENTRYPOINT ["python3", "triqee_sovereign_appliance_engine.py"]
