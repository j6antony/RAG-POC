FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .

#techinically it will work without --no-cache-dir but it is better to cleare the existing stuff especially since we are working with large dependencies
RUN pip install --no-cache-dir torch==2.14.0 \
    --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

EXPOSE 8000


#this line starts fastapi
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]

