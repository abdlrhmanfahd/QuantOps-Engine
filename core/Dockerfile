FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY market_stream.py .

CMD ["python", "-u", "market_stream.py"]
