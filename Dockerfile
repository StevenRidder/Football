FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port
EXPOSE 9876

# Set environment variables
ENV FLASK_APP=app_flask.py
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python3", "app_flask.py"]

