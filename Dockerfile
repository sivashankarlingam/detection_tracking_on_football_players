FROM python:3.9-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV CACHE_BUST=7
WORKDIR /app
RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6 libgl1 libglib2.0-0 git && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 7860
CMD python manage.py migrate && python manage.py collectstatic --noinput && gunicorn Football_Player_Detection_and_Tracking.wsgi:application --bind 0.0.0.0:7860
