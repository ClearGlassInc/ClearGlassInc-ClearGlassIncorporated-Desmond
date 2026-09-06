FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY migrations ./migrations

# Drop root: the control plane handles payments and the approval gate, so a container
# escape should not land on a root shell. Nothing in the image is written at runtime.
RUN useradd --system --create-home --uid 10001 commerce \
    && chown -R commerce:commerce /app
USER commerce

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
