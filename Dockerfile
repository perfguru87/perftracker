# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /usr/src/app/

# Install system dependencies
RUN apt-get update && apt-get install -y libpq-dev gcc libldap2-dev libsasl2-dev

# Install dependencies
COPY requirements.txt /usr/src/app/

# Create a virtual environment in the container at /usr/src/app/venv
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /usr/src/app/

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define command to run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "perftracker_django.wsgi:application"]