FROM python:3.11-slim

WORKDIR /app

# Install curl for the Docker health check used in docker-compose.yml.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY rag/ ./rag/
COPY scripts/ ./scripts/
COPY cred.json ./
COPY langgraph.json ./

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
