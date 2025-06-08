#!/bin/bash

# Crear directorios de logs si no existen
mkdir -p /home/LogFiles
mkdir -p /home/site/wwwroot/logs

# Configurar variables de entorno
export PYTHONPATH=/home/site/wwwroot
export FLASK_APP=app:app
export FLASK_ENV=production
export WEBSITES_PORT=8000

# Instalar dependencias
echo "=== Instalando dependencias ==="
pip install --upgrade pip
pip install -r /home/site/wwwroot/requirements.txt

# Descargar datos de NLTK
echo "=== Descargando datos de NLTK ==="
python -m nltk.downloader -d /home/site/wwwroot/nltk_data punkt
python -m nltk.downloader -d /home/site/wwwroot/nltk_data stopwords

# Establecer la ruta de datos de NLTK
export NLTK_DATA=/home/site/wwwroot/nltk_data

# Iniciar la aplicación con Gunicorn
echo "=== Iniciando la aplicación con Gunicorn ==="
exec gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class gthread \
    --threads 4 \
    --timeout 300 \
    --access-logfile /home/LogFiles/gunicorn-access.log \
    --error-logfile /home/LogFiles/gunicorn-error.log \
    --capture-output \
    --enable-stdio-inheritance \
    --log-level info \
    app:app
