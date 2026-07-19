FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dépendances système (psycopg2, cryptography)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY appProjet/ /app/

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "appProjet.wsgi:application", "--bind", "0.0.0.0:8000"]