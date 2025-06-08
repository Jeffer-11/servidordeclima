#!/bin/bash

# Configurar variables de entorno
export PYTHONPATH="/home/site/wwwroot"

# Crear directorio de logs si no existe
mkdir -p /home/LogFiles

# Iniciar Gunicorn
echo "Iniciando Gunicorn..."
exec gunicorn --bind=0.0.0.0:8000 \
              --workers 4 \
              --timeout 300 \
              --chdir /home/site/wwwroot \
              --access-logfile /home/LogFiles/gunicorn-access.log \
              --error-logfile /home/LogFiles/gunicorn-error.log \
              --log-level info \
              app:app
