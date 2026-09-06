FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

COPY services/clearglass_agent_service/requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip && python -m pip install --no-cache-dir -r requirements.txt

COPY services/clearglass_agent_service ./clearglass_agent_service

EXPOSE 8080

CMD uvicorn clearglass_agent_service.main:app --host 0.0.0.0 --port ${PORT}
