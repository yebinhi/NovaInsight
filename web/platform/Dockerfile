FROM python:3.12-slim

WORKDIR /app

COPY web/platform/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY web/platform /app
COPY cloud/database/schema.sql /app/schema.sql

ENV SCHEMA_PATH=/app/schema.sql
EXPOSE 8080

CMD ["python", "server.py"]
