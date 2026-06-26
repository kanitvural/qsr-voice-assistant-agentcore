FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim
WORKDIR /app

# Configure UV for container environment (no venv, compile bytecode for speed)
ENV UV_SYSTEM_PYTHON=1 UV_COMPILE_BYTECODE=1

# Install system dependencies for PyAudio and other packages
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    gcc \
    g++ \
    make \
    libasound2-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (cache-friendly layer ordering)
COPY requirements.txt .
RUN uv pip install -r requirements.txt

# Install OpenTelemetry for distributed tracing and observability
RUN uv pip install aws-opentelemetry-distro>=0.10.1

# Set AWS region
ENV AWS_REGION=us-east-1
ENV AWS_DEFAULT_REGION=us-east-1

# Signal that this is running in a container
ENV DOCKER_CONTAINER=1

# Security: run as non-root user
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

EXPOSE 8080

# Copy application code
COPY qsr_agent.py .
COPY jwt_auth.py .

# Health check to verify the agent is responsive
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# OpenTelemetry auto-instrumentation wraps the Python process to capture
# all HTTP, boto3, and framework calls for distributed tracing in CloudWatch
CMD ["opentelemetry-instrument", "python", "qsr_agent.py"]