FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY config.json .
COPY pytest.ini .
COPY src/ /app/src/
COPY test/ /app/test/

CMD ["python3", "main.py"]
