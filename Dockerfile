FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .
COPY templates/ templates/
COPY icons/ icons/
COPY rent_scanner/ rent_scanner/
COPY data/ data/

CMD ["python", "bot.py"]