From python:3.14-slim

WORKDIR /app

COPY requirements.txt .

#techinically it will work without --no-cache-dir but it is better to cleare the existing stuff especially since we are working with large dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

RUN mkdir -p "/app/Raw Data" /app/chromadb

WORKDIR /app/src

EXPOSE 8000


#this line starts fastapi
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]

