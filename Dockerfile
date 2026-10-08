FROM python:3.14-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

RUN mkdir -p "/app/Raw Data" /app/chroma_db

WORKDIR /app/src

EXPOSE 8000


#this line starts fastapi
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]

