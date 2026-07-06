FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-rus \
    tesseract-ocr-ukr \
    tesseract-ocr-deu \
    tesseract-ocr-pol \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .
COPY templates/ templates/
COPY icons/ icons/
COPY rent_scanner/ rent_scanner/
COPY services/ services/
COPY handlers/ handlers/
COPY web_scanner/ web_scanner/

CMD ["python", "bot.py"]