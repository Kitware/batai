FROM python:3-slim

RUN pip install --no-cache-dir minio

COPY mock_server.py /app/mock_server.py
WORKDIR /app

CMD ["python", "mock_server.py"]
