# Multi-stage build for smaller image size
FROM python:3.12-slim as builder

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install uv for faster dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files and README (required by pyproject.toml metadata)
COPY pyproject.toml uv.lock README.md ./

# Install dependencies to a virtual environment
RUN uv venv /opt/venv && \
    uv pip install --python /opt/venv/bin/python .

# Final stage
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONOPTIMIZE=1

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy the application
COPY . .

# Pre-compile Python files for faster startup
RUN python -m compileall -b src/

# Create cache directory
RUN mkdir -p .cache-data

# Expose port
EXPOSE 8080

# Set default environment variables for Cloud Run
ENV PORT=8080
ENV HOST=0.0.0.0
ENV DEBUG=False

# Run the application with gunicorn
# Using 1 worker for faster startup and lower memory usage
# Using preload to load application before forking
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "120", "--preload", "src.app:server"]
