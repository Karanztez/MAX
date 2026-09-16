# ==============================================================================
# MAX AI Agent — Production Container Image for GitHub Packages (ghcr.io)
# ==============================================================================

FROM python:3.12-slim

LABEL org.opencontainers.image.title="MAX AI Agent"
LABEL org.opencontainers.image.description="Multi-Provider AI Assistant & Autonomous Tool Runner SDK"
LABEL org.opencontainers.image.source="https://github.com/Karanztez/MAX"
LABEL org.opencontainers.image.licenses="Non-Commercial / Proprietary"

WORKDIR /app

# Install git and essential system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy project configuration and requirements
COPY pyproject.toml setup.py requirements.txt README.md main.py /app/
COPY src/ /app/src/
COPY max_ai/ /app/max_ai/
COPY skills/ /app/skills/

# Install python dependencies and install package in editable mode
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=1

# Default entrypoint runs MAX CLI
ENTRYPOINT ["max"]
CMD ["--help"]
