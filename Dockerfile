# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and uv.lock first for better caching
COPY pyproject.toml uv.lock ./

# Install uv for faster dependency management
RUN pip install uv

# Install dependencies without building the local package
RUN uv pip install -r pyproject.toml --system

# Copy the rest of the application
COPY . .

# Create cache directory
RUN mkdir -p .cache-data

# Expose port
EXPOSE 8080

# Set default environment variables for Cloud Run
ENV PORT=8080
ENV HOST=0.0.0.0
ENV DEBUG=False

# Run the application with gunicorn
CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120", "src.app:server"]
