# Use an official lightweight Python image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create and set the working directory
WORKDIR /app

# Install system dependencies for OpenCV and general tooling
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1 \
    git \
 && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port that the Django app runs on
EXPOSE 7860

# Command to run the application using Gunicorn
# Hugging Face spaces use port 7860 by default
CMD ["gunicorn", "Football_Player_Detection_and_Tracking.wsgi:application", "--bind", "0.0.0.0:7860"]
