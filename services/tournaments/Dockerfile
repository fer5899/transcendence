# Base image with Python
FROM python:3.10

# Set working directory
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get update \
    && apt-get install -y netcat-openbsd

# Copy the Django project files
COPY . /app/

# Set environment variables for Django
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Expose the port Django will use
EXPOSE 8003

# Run Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8003"]
