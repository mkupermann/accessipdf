# Dockerfile for accessipdf with Streamlit GUI
# Multi-stage build for smaller final image

# Stage 1: Build stage with all dependencies
FROM python:3.12-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install veraPDF (for PDF/UA-1 validation)
RUN apt-get install -y verapdf

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e '.[dev]'

# Stage 2: Runtime stage
FROM python:3.12-slim

# Install runtime dependencies
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install veraPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    verapdf \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create app directory
WORKDIR /app

# Copy application files
COPY accessipdf/ ./accessipdf/
COPY gui/ ./gui/
COPY scripts/ ./scripts/
COPY pyproject.toml .
COPY README.md .
COPY LICENSE .
COPY CONTRIBUTING.md .
COPY Makefile .
COPY .gitignore .

# Set environment variables
ENV APP_HOME=/app \
    PYTHONPATH=/app

# Create directories for file uploads and outputs
RUN mkdir -p /app/uploads /app/outputs /app/quarantine /app/templates

# Expose port for Streamlit
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import accessipdf; print('OK')" || exit 1

# Default command: Run Streamlit GUI
CMD ["streamlit", "run", "gui/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]

# Alternative command to run CLI (uncomment to use)
# CMD ["python", "-m", "accessipdf.cli"]
