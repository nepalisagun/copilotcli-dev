FROM python:3.11 AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY data ./data
COPY models ./models

FROM python:3.11

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app/src ./src
COPY --from=builder /app/data ./data
COPY --from=builder /app/models ./models
COPY requirements.txt .

EXPOSE 8000 8080

ENV PYTHONUNBUFFERED=1

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "src.api_main:app"]
