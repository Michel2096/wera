FROM python:3.12-slim

# Evita archivos .pyc y fuerza salida sin buffer (mejor para logs en Docker)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias del sistema necesarias para Pillow/qrcode
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs

EXPOSE 5000

# eventlet + Flask-SocketIO recomiendan ejecutar directamente app.py
# (gunicorn con worker eventlet es la alternativa para producción)
CMD ["python", "app.py"]
