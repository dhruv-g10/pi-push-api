FROM python:3.11-slim

WORKDIR /app

# Install system utilities (curl, procps for psutil)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ /app/server/
RUN mkdir -p /app/uploads

ENV PI_PUSH_HOST=0.0.0.0
ENV PI_PUSH_PORT=8000
ENV PI_PUSH_BASE_DIR=/app/uploads
ENV PI_PUSH_ALLOW_ABSOLUTE_PATHS=true
ENV PI_PUSH_ENABLE_EXEC=true

EXPOSE 8000

CMD ["python", "-m", "server.app.main"]
