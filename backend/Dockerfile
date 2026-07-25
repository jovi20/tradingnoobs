# Backend Dockerfile
FROM python:3.13.5-slim

WORKDIR /app

# Install dependencies
COPY requirements.lock.txt .
RUN python -m pip install --no-cache-dir --upgrade pip==26.1.2 \
    && python -m pip install --no-cache-dir --require-hashes -r requirements.lock.txt

# Copy application
COPY . .

# Create uploads directory
RUN mkdir -p uploads

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
