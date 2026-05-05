FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir confluent-kafka==2.4.0 faker==24.11.0

COPY producer.py .

CMD ["python", "producer.py"]
