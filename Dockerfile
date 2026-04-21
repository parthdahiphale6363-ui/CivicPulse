FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for sentence-transformers and other libs
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure static/uploads exists in the container (though we will mount over it)
RUN mkdir -p /data/static/uploads

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "wsgi:app"]
