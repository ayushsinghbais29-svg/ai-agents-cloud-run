# Dockerfile Configuration

# Use the official Python image from the Docker Hub.
FROM python:3.9-slim

# Set environment variables for Django
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files into the container
COPY . .

# Command to run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "myproject.wsgi:application"]