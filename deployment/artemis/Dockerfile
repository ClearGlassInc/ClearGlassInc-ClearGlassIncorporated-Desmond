# Build from the repository root, not from deployment/artemis:
#   docker build -f deployment/artemis/Dockerfile -t artemis-model .
# main.py mounts artemis.osint, which lives at the root, outside this folder.
FROM python:3.11.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*
COPY deployment/artemis/app/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip==24.3.1 && pip install -r /app/requirements.txt
COPY deployment/artemis/app /app
COPY artemis/__init__.py /app/artemis/__init__.py
COPY artemis/osint /app/artemis/osint
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
