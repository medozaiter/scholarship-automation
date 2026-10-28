FROM python:3.11-slim

WORKDIR /app

# Install basic system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Hugging Face Spaces runs as user with UID 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONPATH=/app

WORKDIR /app

# Copy application files with proper user ownership
COPY --chown=user:user . .

# Ensure data directory exists and is writable
RUN mkdir -p data

# Hugging Face Spaces listens on port 7860
EXPOSE 7860

CMD ["sh", "-c", "uvicorn web.app:app --host 0.0.0.0 --port ${PORT:-7860}"]
