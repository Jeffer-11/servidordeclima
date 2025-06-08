#!/bin/bash

# Crear directorios necesarios
mkdir -p /home/LogFiles/app

# Configurar variables de entorno
export PYTHONPATH="/home/site/wwwroot"
export FLASK_APP="app:app"
export FLASK_ENV="production"

# Instalar dependencias
echo "Instalando dependencias..."
pip install -r /home/site/wwwroot/requirements.txt

# Descargar modelos de NLTK
echo "Descargando recursos de NLTK..."
python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('wordnet', quiet=True)"

# Iniciar Gunicorn
echo "Iniciando Gunicorn..."
exec gunicorn \
    --bind=0.0.0.0:8000 \
    --workers 4 \
    --timeout 300 \
    --chdir /home/site/wwwroot \
    --access-logfile /home/LogFiles/app/access.log \
    --error-logfile /home/LogFiles/app/error.log \
    --log-level info \
    --capture-output \
    --enable-stdio-inheritance \
    --log-syslog \
    --worker-class sync \
    --worker-tmp-dir /dev/shm \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --log-file=- \
    app:app
