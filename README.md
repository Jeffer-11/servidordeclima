# Servidor de Chatbot de Clima

Este es un servidor Flask que proporciona una API para un chatbot de clima. El chatbot puede proporcionar información meteorológica actual, pronósticos y datos de zonas horarias.

## Configuración Requerida en Azure

### Variables de Entorno
Asegúrate de configurar las siguientes variables en la configuración de tu App Service en Azure Portal:

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `PYTHON_VERSION` | 3.11 | Versión de Python a utilizar |
| `WEBSITES_PORT` | 8000 | Puerto en el que se ejecutará la aplicación |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | 1 | Habilita la instalación de dependencias durante el despliegue |

| `gunicorn app:app` | gunicorn app:app | Comando para iniciar la aplicación con Gunicorn |
### Configuración de la Aplicación
1. Ve a tu App Service en Azure Portal
2. Navega a "Configuración" > "Configuración"
3. En la pestaña "Configuración de la aplicación", agrega las variables mencionadas anteriormente
4. Haz clic en "Guardar"

## Estructura del Proyecto

```
.
├── app.py              # Aplicación principal de Flask
├── requirements.txt    # Dependencias de Python
├── runtime.txt        # Versión de Python
├── startup.sh         # Script de inicio para Azure
└── web.config         # Configuración de IIS para Azure
```

## Despliegue Automático

1. Conecta tu repositorio de GitHub a Azure App Service
2. Configura el despliegue continuo
3. Azure se encargará automáticamente de instalar dependencias y reiniciar la aplicación

## Endpoints de la API

### Prueba de conexión
- **Método**: GET
- **Ruta**: `/test`
- **Respuesta**:
  ```json
  {
      "status": "ok",
      "message": "La API está funcionando correctamente",
      "version": "1.0.0"
  }
  ```

### Chat del Clima
- **Método**: POST
- **Ruta**: `/chat`
- **Cuerpo de la solicitud**:
  ```json
  {
      "mensaje": "¿Qué clima hace en Madrid?"
  }
  ```
- **Respuesta de ejemplo**:
  ```json
  {
      "respuesta": "El clima actual en Madrid es...",
      "ubicacion": "Madrid, ES",
      "temperatura": "22°C",
      "descripcion": "Cielo despejado"
  }
  ```

## Solución de Problemas

### Verificación de Logs
1. En Azure Portal, ve a tu App Service
2. Navega a "Supervisión" > "Registros de streaming"
3. Revisa los mensajes de error o advertencia

### Revisar Variables de Entorno
Asegúrate de que todas las variables de entorno estén correctamente configuradas y con los valores adecuados.

## Soporte

Para soporte, por favor abre un issue en el repositorio o contacta al administrador del sistema.
