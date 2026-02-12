FROM python:3.11 AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY knowledge ./knowledge
COPY models ./models

FROM python:3.11

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app/src ./src
COPY --from=builder /app/knowledge ./knowledge
COPY --from=builder /app/models ./models
COPY requirements.txt .

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

# Health check for Docker
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

