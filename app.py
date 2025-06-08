"""
Weather Chatbot Application

This module provides a Flask-based web application that serves as a weather chatbot.
It allows users to get weather information and time for different locations.
"""
import json
import logging
import os
from datetime import datetime
from functools import lru_cache
from typing import Dict, List, Optional, Tuple, Any, Union
import time

import spacy
import pytz
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from timezonefinder import TimezoneFinder
from spacy.lang.es.stop_words import STOP_WORDS as STOP_WORDS_SPACY
from string import punctuation

# API Configuration
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "5ca6fd1a510cf911fd089dcd10179cb9")
OPENWEATHER_BASE_URL = "https://api.openweathermap.org"
GEOCODING_ENDPOINT = "/geo/1.0/direct"
WEATHER_ENDPOINT = "/data/2.5/weather"
REVERSE_GEOCODING_ENDPOINT = "/geo/1.0/reverse"

# Request Configuration
TIMEOUT = 15  # seconds
MAX_RETRIES = 3

# Chatbot Configuration
SALUDOS = ["hola", "buenos días", "buenas tardes", "buenas noches", "hey", "saludos"]
PALABRAS_CLIMA = ["clima", "tiempo", "temperatura", "pronóstico", "hace calor", "hace frío"]
PALABRAS_HORA = ["hora", "qué horas son", "dime la hora"]

# Weather Icons Mapping
WEATHER_ICONS = {
    '01': '☀️',  # clear sky
    '02': '⛅',  # few clouds
    '03': '☁️',  # scattered clouds
    '04': '☁️',  # broken clouds
    '09': '🌧️',  # shower rain
    '10': '🌦️',  # rain
    '11': '⛈️',  # thunderstorm
    '13': '❄️',   # snow
    '50': '🌫️'    # mist
}

# Weather Conditions in Spanish
CONDICIONES_TRADUCIDAS = {
    'clear': 'Despejado',
    'clouds': 'Nublado',
    'few clouds': 'Parcialmente nublado',
    'scattered clouds': 'Nubes dispersas',
    'broken clouds': 'Mayormente nublado',
    'overcast clouds': 'Muy nublado',
    'rain': 'Lluvia',
    'light rain': 'Lluvia ligera',
    'moderate rain': 'Lluvia moderada',
    'heavy intensity rain': 'Lluvia intensa',
    'thunderstorm': 'Tormenta',
    'snow': 'Nieve',
    'mist': 'Neblina',
    'fog': 'Niebla',
    'haze': 'Neblina',
    'drizzle': 'Llovizna'
}

# Countries and their capitals
PAISES_INFO = {
    'chile': {'capital': 'Santiago', 'codigo': 'CL'},
    'argentina': {'capital': 'Buenos Aires', 'codigo': 'AR'},
    'españa': {'capital': 'Madrid', 'codigo': 'ES'},
    'mexico': {'capital': 'Ciudad de México', 'codigo': 'MX'},
    'colombia': {'capital': 'Bogotá', 'codigo': 'CO'},
    'peru': {'capital': 'Lima', 'codigo': 'PE'},
    'venezuela': {'capital': 'Caracas', 'codigo': 'VE'},
    'ecuador': {'capital': 'Quito', 'codigo': 'EC'},
    'bolivia': {'capital': 'La Paz', 'codigo': 'BO'},
    'paraguay': {'capital': 'Asunción', 'codigo': 'PY'},
    'uruguay': {'capital': 'Montevideo', 'codigo': 'UY'},
    'brasil': {'capital': 'Brasilia', 'codigo': 'BR'},
    'estados unidos': {'capital': 'Washington', 'codigo': 'US'},
    'canada': {'capital': 'Ottawa', 'codigo': 'CA'},
    'francia': {'capital': 'París', 'codigo': 'FR'},
    'italia': {'capital': 'Roma', 'codigo': 'IT'},
    'alemania': {'capital': 'Berlín', 'codigo': 'DE'},
    'reino unido': {'capital': 'Londres', 'codigo': 'GB'},
    'japon': {'capital': 'Tokio', 'codigo': 'JP'},
    'china': {'capital': 'Pekín', 'codigo': 'CN'},
    'rusia': {'capital': 'Moscú', 'codigo': 'RU'}
}

# Capital cities by country for weather lookups
CIUDADES_POR_PAIS = {
    'argentina': 'Buenos Aires',
    'bolivia': 'La Paz',
    'brasil': 'Brasilia',
    'canada': 'Ottawa',
    'chile': 'Santiago',
    'colombia': 'Bogotá',
    'costa rica': 'San José',
    'cuba': 'La Habana',
    'ecuador': 'Quito',
    'el salvador': 'San Salvador',
    'españa': 'Madrid',
    'estados unidos': 'Washington',
    'guatemala': 'Ciudad de Guatemala',
    'honduras': 'Tegucigalpa',
    'mexico': 'Ciudad de México',
    'nicaragua': 'Managua',
    'panama': 'Ciudad de Panamá',
    'paraguay': 'Asunción',
    'peru': 'Lima',
    'puerto rico': 'San Juan',
    'republica dominicana': 'Santo Domingo',
    'uruguay': 'Montevideo',
    'venezuela': 'Caracas'
}

# Special city mappings (kept for backward compatibility)
CIUDADES_ESPECIALES = {
    'paris': 'París,FR',
    'berlin': 'Berlín,DE',
    'rome': 'Roma,IT',
    'tokyo': 'Tokio,JP',
    'sydney': 'Sídney,AU',
    'moscow': 'Moscú,RU',
    'beijing': 'Pekín,CN',
    'washington': 'Washington,US',
    'new york': 'Nueva York,US',
    'london': 'Londres,GB',
    'madrid': 'Madrid,ES',
    'barcelona': 'Barcelona,ES'
}

# Days of the week in Spanish
DIAS_SEMANA = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cargar el modelo de spaCy en español
try:
    nlp = spacy.load('es_core_news_sm')
except OSError:
    print("Por favor instala el modelo de español de spaCy ejecutando: python -m spacy download es_core_news_sm")
    raise

# Initialize Flask app
app = Flask(__name__)

# Configuración de CORS para producción
cors = CORS(app, resources={
    r"/*": {
        "origins": [
            "chatbotclima-b3dudba5fndahshv.centralus-01.azurewebsites.net",  # Tu dominio real en Azure
            "http://localhost:3000",  # Para pruebas locales
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

class WeatherAPIError(Exception):
    """Custom exception for Weather API errors."""
    pass

# Update ZONAS_HORARIAS_PAIS with more specific entries
ZONAS_HORARIAS_PAIS = {
    # Rusia y sus zonas horarias principales
    'RU': [
        'Europe/Moscow',        # UTC+3 (Moscú)
        'Europe/Kaliningrad',   # UTC+2
        'Europe/Samara',        # UTC+4
        'Asia/Yekaterinburg',   # UTC+5
        'Asia/Omsk',           # UTC+6
        'Asia/Krasnoyarsk',    # UTC+7
        'Asia/Irkutsk',        # UTC+8
        'Asia/Yakutsk',        # UTC+9
        'Asia/Vladivostok',    # UTC+10
        'Asia/Magadan',        # UTC+11
        'Asia/Kamchatka'       # UTC+12
    ],
    # Estados Unidos
    'US': [
        'America/New_York',     # Este
        'America/Chicago',      # Central
        'America/Denver',       # Montaña
        'America/Los_Angeles',  # Pacífico
        'America/Anchorage',    # Alaska
        'Pacific/Honolulu'      # Hawái
    ],
    # Europa
    'ES': ['Europe/Madrid'],
    'FR': ['Europe/Paris'],
    'DE': ['Europe/Berlin'],
    'IT': ['Europe/Rome'],
    'GB': ['Europe/London'],
    'PT': ['Europe/Lisbon'],
    # América Latina
    'MX': [
        'America/Mexico_City',
        'America/Tijuana',
        'America/Cancun'
    ],
    'BR': [
        'America/Sao_Paulo',
        'America/Manaus',
        'America/Belem'
    ],
    'AR': ['America/Argentina/Buenos_Aires'],
    'CL': ['America/Santiago'],
    'CO': ['America/Bogota'],
    'PE': ['America/Lima'],
    'EC': ['America/Guayaquil'],
    'VE': ['America/Caracas'],
    'BO': ['America/La_Paz'],
    'PY': ['America/Asuncion'],
    'UY': ['America/Montevideo'],
    'CR': ['America/Costa_Rica'],
    'DO': ['America/Santo_Domingo'],
    'PA': ['America/Panama'],
    'HN': ['America/Tegucigalpa'],
    'SV': ['America/El_Salvador'],
    'NI': ['America/Managua'],
    'GT': ['America/Guatemala']
}

class ChatbotClima:
    def obtener_zona_horaria(self, lat: float, lon: float, codigo_pais: str = None, pais_usuario: str = None) -> dict:
        """Obtiene la zona horaria y hora local basada en coordenadas y código de país."""
        try:
            # Determinar la zona horaria
            if pais_usuario and pais_usuario.lower() in PAISES_INFO:
                codigo_pais = PAISES_INFO[pais_usuario.lower()]['codigo']
                logger.info(f"🌍 Usando código de país del usuario: {codigo_pais}")
                
                if codigo_pais in ZONAS_HORARIAS_PAIS:
                    timezone_str = ZONAS_HORARIAS_PAIS[codigo_pais][0]
                    logger.info(f"🌍 Usando zona horaria predefinida: {timezone_str}")
                else:
                    timezone_str = self.tf.timezone_at(lat=lat, lng=lon)
                    logger.info(f"🌍 Zona horaria determinada por coordenadas: {timezone_str}")
            else:
                timezone_str = self.tf.timezone_at(lat=lat, lng=lon)
                logger.info(f"🌍 Zona horaria determinada por coordenadas: {timezone_str}")

            if not timezone_str:
                logger.error("❌ No se pudo determinar la zona horaria")
                return {'error': 'No se pudo determinar la zona horaria'}

            # Obtener hora local
            try:
                # Crear timezone y obtener hora UTC actual
                timezone = pytz.timezone(timezone_str)
                utc_now = datetime.now(pytz.UTC)
                local_time = utc_now.astimezone(timezone)

                # Formatear hora
                hora = local_time.strftime("%H:%M")  # 24h format
                hora_12 = local_time.strftime("%I:%M %p").lower().replace("pm", "p.m.").replace("am", "a.m.")
                
                # Determinar momento del día
                hora_num = local_time.hour
                if 5 <= hora_num < 12:
                    momento = "de la mañana"
                elif 12 <= hora_num < 20:
                    momento = "de la tarde"
                else:
                    momento = "de la noche"

                # Traducir día
                dias_es = {
                    'Monday': 'lunes', 'Tuesday': 'martes', 'Wednesday': 'miércoles',
                    'Thursday': 'jueves', 'Friday': 'viernes', 'Saturday': 'sábado', 
                    'Sunday': 'domingo'
                }
                weekday_es = dias_es[local_time.strftime("%A")]

                return {
                    'timezone': timezone_str,
                    'time': hora,
                    'time_12': hora_12,
                    'moment': momento,
                    'weekday': weekday_es
                }

            except pytz.exceptions.UnknownTimeZoneError as e:
                logger.error(f"Error de zona horaria: {str(e)}")
                return {'error': f'Zona horaria no reconocida: {str(e)}'}

        except Exception as e:
            logger.error(f"Error al obtener zona horaria: {str(e)}")
            return {'error': str(e)}

    """Chatbot for providing weather and time information."""
    
    def __init__(self):
        """Initialize the chatbot with configuration."""
        self.saludos = SALUDOS
        self.palabras_clima = PALABRAS_CLIMA
        self.palabras_hora = PALABRAS_HORA
        self.paises_info = PAISES_INFO
        self.ciudades_especiales = CIUDADES_ESPECIALES
        self.tf = TimezoneFinder()
        
        # Configuración spaCy
        self.nlp = nlp  # Usamos el modelo cargado globalmente
        self.stop_words = STOP_WORDS_SPACY
        self.puntuacion = set(punctuation)
        
        self.weather_api_key = os.getenv('OPENWEATHER_API_KEY')
        self.geocoding_api_key = os.getenv('GEOCODING_API_KEY')
        
    def _limpiar_texto(self, texto: str) -> List[str]:
        """
        Limpia el texto eliminando stopwords y puntuación usando spaCy.
        
        Args:
            texto: Texto a limpiar
            
        Returns:
            Lista de tokens limpios
        """
        if not texto:
            return []
            
        try:
            doc = self.nlp(texto.lower())
            return [token.lemma_ for token in doc 
                   if not token.is_stop 
                   and not token.is_punct 
                   and not token.is_space
                   and token.text.strip() != '']
        except Exception as e:
            logging.error(f"Error al limpiar texto: {e}")
            return []

    def _es_palabra_similar(self, palabra1: str, palabra2: str, umbral: float = 0.8) -> bool:
        """
        Verifica si dos palabras son similares usando los embeddings de spaCy.
        
        Args:
            palabra1: Primera palabra a comparar
            palabra2: Segunda palabra a comparar
            umbral: Umbral de similitud (0-1)
            
        Returns:
            bool: True si las palabras son similares, False en caso contrario
        """
        if not palabra1 or not palabra2:
            return False
            
        # Usar los embeddings de spaCy para calcular similitud semántica
        doc1 = self.nlp(palabra1.lower())
        doc2 = self.nlp(palabra2.lower())
        
        # Si alguno de los tokens no tiene vector, usar distancia de Levenshtein como respaldo
        if not doc1.vector_norm or not doc2.vector_norm:
            import Levenshtein
            distancia = Levenshtein.distance(palabra1.lower(), palabra2.lower())
            longitud_max = max(len(palabra1), len(palabra2))
            return (1 - (distancia / longitud_max)) >= umbral
            
        # Calcular similitud de coseno entre los vectores
        return doc1.similarity(doc2) >= umbral

    def _make_api_request(self, endpoint: str, params: Dict) -> Dict:
        """Make an HTTP request to the OpenWeather API."""
        if not params:
            params = {}
            
        # Always include API key
        params['appid'] = OPENWEATHER_API_KEY
        
        # Construct the full URL properly
        url = f"{OPENWEATHER_BASE_URL}{endpoint}"
        
        logger.info(f"🔵 Realizando solicitud a: {url}")
        logger.info(f"🔵 Parámetros: {params}")
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(url, params=params, timeout=TIMEOUT)
                
                # Log response info
                logger.info(f"🔵 Código de estado: {response.status_code}")
                
                # Parse JSON response
                data = response.json()
                
                if response.status_code != 200:
                    error_msg = data.get('message', 'Error desconocido')
                    raise WeatherAPIError(f"Error en la API: {error_msg}")
                    
                return data
                
            except Exception as e:
                logger.error(f"❌ Intento {attempt + 1} fallido: {str(e)}")
                if attempt == MAX_RETRIES - 1:
                    raise WeatherAPIError(f"Error después de {MAX_RETRIES} intentos: {str(e)}")
                time.sleep((attempt + 1) * 2)

    def obtener_coordenadas(self, ubicacion: str, codigo_pais: str = None) -> Tuple[Optional[str], Optional[float], Optional[float], Optional[str]]:
        """Obtiene las coordenadas de una ubicación. Si se provee código de país, lo usa para mayor precisión."""
        try:
            params = {
                'q': ubicacion if not codigo_pais else f"{ubicacion},{codigo_pais}",
                'limit': 1
            }
            data = self._make_api_request(GEOCODING_ENDPOINT, params)
            if data and len(data) > 0:
                location = data[0]
                return (
                    location.get('name'),
                    location.get('lat'),
                    location.get('lon'),
                    location.get('country')
                )
            return None, None, None, None
        except Exception as e:
            logger.error(f"❌ Error al obtener coordenadas: {str(e)}")
            return None, None, None, None

    def obtener_clima_por_coordenadas(self, lat: float, lon: float) -> Dict:
        """Obtiene el clima actual usando las coordenadas."""
        try:
            # Get weather data
            params = {
                'lat': lat,
                'lon': lon,
                'units': 'metric',
                'lang': 'es'
            }
            
            weather_data = self._make_api_request(WEATHER_ENDPOINT, params)
            
            if not weather_data:
                raise WeatherAPIError("No se pudieron obtener datos del clima")
                
            # Get location name through reverse geocoding
            geocoding_params = {
                'lat': lat,
                'lon': lon,
                'limit': 1
            }
            
            location_data = self._make_api_request(REVERSE_GEOCODING_ENDPOINT, geocoding_params)
            
            # Get location name
            if location_data and len(location_data) > 0:
                nombre_ubicacion = location_data[0].get('name', 'Desconocido')
                codigo_pais = location_data[0].get('country', '')
            else:
                nombre_ubicacion = "Ubicación"
                codigo_pais = ""
                
            # Get timezone info
            timezone_info = self.obtener_zona_horaria(lat, lon, codigo_pais)
            
            # Extract weather data
            weather = weather_data['weather'][0]
            main = weather_data['main']
            wind = weather_data.get('wind', {})
            
            # Obtener fecha local (día completo) y hora local usando la zona horaria
            fecha_local = ""
            hora_local = ""
            try:
                if timezone_info.get('timezone'):
                    tz = pytz.timezone(timezone_info['timezone'])
                    now = datetime.now(tz)
                    # Ejemplo: "sábado, 8 de junio de 2024"
                    fecha_local = now.strftime("%A, %-d de %B de %Y")
                    hora_local = now.strftime("%H:%M")
                    # Traducir meses y días si es necesario
                    meses = {
                        'january': 'enero', 'february': 'febrero', 'march': 'marzo', 'april': 'abril',
                        'may': 'mayo', 'june': 'junio', 'july': 'julio', 'august': 'agosto',
                        'september': 'septiembre', 'october': 'octubre', 'november': 'noviembre', 'december': 'diciembre'
                    }
                    dias = {
                        'monday': 'lunes', 'tuesday': 'martes', 'wednesday': 'miércoles', 'thursday': 'jueves',
                        'friday': 'viernes', 'saturday': 'sábado', 'sunday': 'domingo'
                    }
                    for en, es in meses.items():
                        fecha_local = fecha_local.replace(en, es)
                    for en, es in dias.items():
                        fecha_local = fecha_local.replace(en, es)
            except Exception:
                fecha_local = ""
                hora_local = ""

            return {
                'location': f"{nombre_ubicacion}{', ' + codigo_pais if codigo_pais else ''}",
                'coordinates': {'lat': lat, 'lon': lon},
                'temp': round(main.get('temp'), 1),
                'feels_like': round(main.get('feels_like'), 1),
                'humidity': main.get('humidity'),
                'wind_speed': round(wind.get('speed', 0) * 3.6, 1),  # m/s to km/h
                'pressure': main.get('pressure'),
                'description': weather.get('description', '').capitalize(),
                'icon': WEATHER_ICONS.get(weather.get('icon', '')[:2], '🌤️'),
                'time': hora_local,  # <-- Hora según la zona horaria correspondiente
                'moment': timezone_info.get('moment', ''),
                'weekday': timezone_info.get('weekday', ''),
                'date': fecha_local  # <-- Día completo según la zona horaria correspondiente
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo clima: {str(e)}")
            raise WeatherAPIError(f"Error al obtener el clima: {str(e)}")

    def obtener_clima_actual(self, ubicacion: str) -> dict:
        """Obtiene el clima actual para una ubicación o país y devuelve un dict estructurado."""
        try:
            ubicacion_lower = ubicacion.lower().strip()
            # Si es país conocido, usar la capital y el código de país
            if ubicacion_lower in PAISES_INFO:
                capital = PAISES_INFO[ubicacion_lower]['capital']
                codigo_pais = PAISES_INFO[ubicacion_lower]['codigo']
                logger.info(f"📍 Usando capital {capital} para país {ubicacion_lower} ({codigo_pais})")
                nombre_ciudad, lat, lon, codigo_pais_resp = self.obtener_coordenadas(capital, codigo_pais)
            else:
                nombre_ciudad, lat, lon, codigo_pais_resp = self.obtener_coordenadas(ubicacion)

            # Si no se encuentra, intentar variantes
            if not all([lat, lon]):
                for pais, info in PAISES_INFO.items():
                    if ubicacion_lower == pais or ubicacion_lower == info['capital'].lower():
                        nombre_ciudad, lat, lon, codigo_pais_resp = self.obtener_coordenadas(info['capital'], info['codigo'])
                        if all([lat, lon]):
                            break

            if not all([lat, lon]):
                logger.warning(f"No pude encontrar la ubicación: {ubicacion}")
                return {'error': f"No pude encontrar la ubicación: {ubicacion}"}

            # Obtener datos del clima
            clima_data = self.obtener_clima_por_coordenadas(lat, lon)
            return clima_data

        except WeatherAPIError as e:
            logger.error(f"Error en API del clima: {str(e)}")
            return {'error': f"Error al obtener el clima: {str(e)}"}
        except Exception as e:
            logger.error(f"Error inesperado: {str(e)}")
            return {'error': "Lo siento, ha ocurrido un error al obtener el clima."}

    @lru_cache(maxsize=128)
    def obtener_hora_ciudad(self, ciudad: str) -> dict:
        """Obtiene la hora actual en una ciudad específica."""
        try:
            # Normalizar ciudad/país
            ciudad_lower = ciudad.lower()
            if ciudad_lower in PAISES_INFO:
                ciudad = PAISES_INFO[ciudad_lower]['capital']
                codigo_pais = PAISES_INFO[ciudad_lower]['codigo']
            else:
                codigo_pais = None

            # Obtener coordenadas y zona horaria
            nombre_ciudad, lat, lon, api_codigo_pais = self.obtener_coordenadas(ciudad)
            
            if not all([lat, lon]):
                return {'error': f"No pude encontrar la ubicación de {ciudad}"}
                
            # Obtener zona horaria
            timezone_info = self.obtener_zona_horaria(lat, lon, api_codigo_pais, pais_usuario=ciudad_lower)
            
            if 'error' in timezone_info:
                return {'error': f"Error al obtener la hora para {ciudad}: {timezone_info['error']}"}
                
            # Formatear respuesta como objeto estructurado
            ubicacion = f"{nombre_ciudad}, {codigo_pais}" if codigo_pais else nombre_ciudad
            
            # Get offset for display
            tz = pytz.timezone(timezone_info['timezone'])
            now = datetime.now(tz)
            offset = now.strftime('%z')
            offset_str = f"GMT{offset[:3]}:{offset[3:]}"
            
            return {
                'type': 'time',
                'location': ubicacion,
                'timezone': timezone_info['timezone'],
                'timezone_display': offset_str,
                'time': timezone_info['time'],
                'time_12': timezone_info['time_12'],
                'moment': timezone_info['moment'],
                'weekday': timezone_info['weekday']
            }
            
        except Exception as e:
            logger.error(f"Error al obtener hora: {str(e)}")
            return {'error': f"Lo siento, ocurrió un error al obtener la hora para {ciudad}"}

    def extraer_entidades(self, texto: str) -> Dict[str, List[str]]:
        """
        Extrae entidades del texto usando spaCy.
        
        Args:
            texto: Texto del que extraer entidades
            
        Returns:
            Diccionario con las entidades encontradas por tipo
        """
        doc = self.nlp(texto)
        entidades = {
            'LOC': [],  # Ubicaciones
            'GPE': [],  # Países, ciudades, estados
            'ORG': [],  # Organizaciones
            'MISC': [],  # Misceláneo
            'es_pais': False,
            'ubicacion': None
        }
        
        # Extraer entidades nombradas
        for ent in doc.ents:
            if ent.label_ in entidades:
                entidades[ent.label_].append(ent.text)
                
                # Si es una ubicación geopolítica (país, ciudad, estado)
                if ent.label_ == 'GPE':
                    pais_normalizado = self._normalizar_pais(ent.text)
                    if pais_normalizado and pais_normalizado in self.paises_info:
                        entidades['es_pais'] = True
                        entidades['ubicacion'] = pais_normalizado
                        break
        
        # Si no se encontró ubicación en las entidades, buscar en el texto tokenizado
        if not entidades['ubicacion']:
            for token in doc:
                if not token.is_stop and not token.is_punct:
                    pais_normalizado = self._normalizar_pais(token.text)
                    if pais_normalizado and pais_normalizado in self.paises_info:
                        entidades['es_pais'] = True
                        entidades['ubicacion'] = pais_normalizado
                        break
        
        # Detectar intenciones usando el texto en minúsculas
        texto_min = texto.lower()
        entidades['es_saludo'] = any(saludo in texto_min for saludo in self.saludos)
        entidades['es_clima'] = any(palabra in texto_min for palabra in self.palabras_clima)
        entidades['es_hora'] = any(palabra in texto_min for palabra in self.palabras_hora)
        
        return entidades

    def procesar_mensaje(self, mensaje: str) -> str:
        """
        Procesa el mensaje del usuario y devuelve una respuesta utilizando spaCy.
        
        Args:
            mensaje: Mensaje del usuario
            
        Returns:
            str: Respuesta del chatbot
        """
        if not mensaje or not isinstance(mensaje, str):
            return "No entendí tu mensaje. ¿Podrías repetirlo?"
        
        # Procesar el mensaje con spaCy
        doc = self.nlp(mensaje.lower())
        
        # Verificar si es un saludo
        if any(token.text in self.saludos for token in doc):
            return "¡Hola! Soy tu asistente del clima. ¿En qué puedo ayudarte hoy?"
        
        # Extraer entidades
        entidades = self.extraer_entidades(mensaje)
        
        # Verificar si se pregunta por el clima
        if any(token.text in self.palabras_clima for token in doc):
            ubicacion = None
            
            # Buscar ubicación en las entidades (GPE para países, ciudades, estados o LOC para ubicaciones)
            if entidades['GPE']:
                ubicacion = entidades['GPE'][0]  # Tomar la primera ubicación encontrada
            elif entidades['LOC']:
                ubicacion = entidades['LOC'][0]
            
            # Si no se encontró en entidades, buscar sustantivos propios
            if not ubicacion:
                for ent in doc.ents:
                    if ent.label_ in ['GPE', 'LOC']:
                        ubicacion = ent.text
                        break
            
            if ubicacion:
                try:
                    clima = self.obtener_clima_actual(ubicacion)
                    if 'error' in clima:
                        return f"No pude obtener el clima para {ubicacion}. ¿Podrías ser más específico?"
                    
                    # Return the structured data instead of formatted text
                    return clima
                except Exception as e:
                    logging.error(f"Error al obtener clima: {e}", exc_info=True)
                    return f"Lo siento, hubo un error al obtener el clima para {ubicacion}."
            else:
                return "¿De qué ubicación te gustaría saber el clima? Por favor, especifica una ciudad o país."
        
        # Verificar si se pregunta por la hora
        elif any(token.text in self.palabras_hora for token in doc):
            ubicacion = None
            
            # Buscar ubicación en las entidades
            if entidades['GPE']:
                ubicacion = entidades['GPE'][0]
            elif entidades['LOC']:
                ubicacion = entidades['LOC'][0]
            
            # Si no se encontró ubicación, usar 'aquí'
            if not ubicacion:
                ubicacion = 'aquí'
                
            try:
                hora_info = self.obtener_hora_ciudad(ubicacion)
                if 'error' in hora_info:
                    return f"No pude obtener la hora para {ubicacion}."
                
                # Return the structured data instead of formatted text
                return hora_info
            except Exception as e:
                logging.error(f"Error al obtener hora: {e}", exc_info=True)
                return f"Lo siento, no pude obtener la hora para {ubicacion}."
        
        # Si no se reconoce la intención, usar similitud de texto para sugerencias
        similitudes = []
        for token in doc:
            # Buscar similitudes con palabras clave conocidas
            if token.text in self.palabras_clima + self.palabras_hora + self.saludos:
                similitudes.append(token.text)
        
        if similitudes:
            return f"No estoy seguro de cómo ayudarte con eso. ¿Te refieres a algo relacionado con: {', '.join(set(similitudes))}?"
        
        return "No estoy seguro de cómo ayudarte. ¿Te gustaría saber el clima o la hora en alguna ubicación? Puedes preguntarme cosas como '¿Qué clima hace en Madrid?' o '¿Qué hora es en Tokio?'"

    def _eliminar_tildes(self, texto: str) -> str:
        """Elimina tildes y caracteres especiales del texto."""
        reemplazos = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ü': 'u', 'ñ': 'n', 'à': 'a', 'è': 'e', 'ì': 'i',
            'ò': 'o', 'ù': 'u'
        }
        return ''.join(reemplazos.get(c, c) for c in texto.lower())
    
    def _normalizar_pais(self, texto: str) -> Optional[str]:
        """Normaliza el nombre del país y maneja variaciones comunes."""
        texto = texto.lower().strip()
        variaciones_paises = {
            # América
            'usa': 'estados unidos',
            'estados unidos de america': 'estados unidos',
            'eeuu': 'estados unidos',
            'united states': 'estados unidos',
            'us': 'estados unidos',
            'méxico': 'mexico',
            'república dominicana': 'republica dominicana',
            'rd': 'republica dominicana',
            'vzla': 'venezuela',
            'arg': 'argentina',
            'chi': 'chile',
            'col': 'colombia',
            'per': 'peru',
            'uru': 'uruguay',
            'par': 'paraguay',
            'ecu': 'ecuador',
            'bol': 'bolivia',
            # Europa
            'españa': 'espana',
            'uk': 'reino unido',
            'gran bretaña': 'reino unido',
            'england': 'reino unido',
            'francia': 'francia',
            'fr': 'francia',
            'alemania': 'alemania',
            'de': 'alemania',
            'italia': 'italia',
            'it': 'italia',
            'portugal': 'portugal',
            'pt': 'portugal',
            # Asia
            'japón': 'japon',
            'jp': 'japon',
            'china': 'china',
            'cn': 'china',
            'corea del sur': 'corea del sur',
            'kr': 'corea del sur',
            # Oceanía
            'australia': 'australia',
            'au': 'australia',
            'nueva zelanda': 'nueva zelanda',
            'nz': 'nueva zelanda'
        }
        pais_normalizado = variaciones_paises.get(texto, texto)
        if pais_normalizado in PAISES_INFO:
            return pais_normalizado
        for pais in PAISES_INFO:
            if pais_normalizado in pais or pais in pais_normalizado:
                return pais
        return None

def create_app():
    """Crea y configura la aplicación Flask."""
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes
    
    # Configuración de la aplicación
    app.config['JSON_AS_ASCII'] = False  # Para soportar caracteres especiales en las respuestas JSON
    
    # Crear una instancia del chatbot
    chatbot = ChatbotClima()
    
    @app.route('/')
    def home():
        """Ruta principal - API status."""
        return jsonify({
            'status': 'ok',
            'message': 'Weather Chatbot API is running',
            'endpoints': {
                'chat': '/chat (POST)',
                'status': '/ (GET)'
            }
        })
    
    @app.route('/chat', methods=['POST', 'OPTIONS'])
    def chat():
        """Maneja las solicitudes de chat del usuario."""
        if request.method == 'OPTIONS':
            # Handle preflight request
            response = jsonify({'status': 'ok'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
            response.headers.add('Access-Control-Allow-Methods', 'POST')
            return response
            
        try:
            # Registrar inicio de solicitud
            logger.info("\n" + "="*80)
            logger.info("📥 NUEVA SOLICITUD RECIBIDA")
            logger.info(f"📝 Método: {request.method}")
            logger.info(f"🌐 URL: {request.url}")
            logger.info(f"📦 Datos de la solicitud: {request.data}")
            
            # Obtener y validar JSON
            try:
                data = request.get_json()
                logger.info(f"📋 Datos JSON recibidos: {json.dumps(data, indent=2)}")
            except Exception as e:
                logger.error(f"❌ Error al decodificar JSON: {str(e)}")
                return jsonify({'error': 'Formato de solicitud inválido'}), 400
            
            # Validar mensaje
            if not data or 'mensaje' not in data:
                logger.error("❌ Falta el campo 'mensaje' en la solicitud")
                return jsonify({'error': 'Formato de solicitud inválido'}), 400
            
            mensaje = data.get('mensaje', '').strip()
            logger.info(f"💬 Mensaje recibido: {mensaje}")

            # Manejar mensajes con coordenadas
            if mensaje.startswith('@coordenadas:'):
                try:
                    # Extraer y validar coordenadas
                    coords = mensaje.replace('@coordenadas:', '').split(',')
                    if len(coords) != 2:
                        raise ValueError("Formato de coordenadas inválido")
                
                    lat = float(coords[0])
                    lon = float(coords[1])
                
                    # Validar rango de coordenadas
                    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                        raise ValueError("Coordenadas fuera de rango")
                
                    # Registrar precisión si está disponible
                    accuracy = data.get('accuracy')
                    if accuracy:
                        logger.info(f"📍 Precisión GPS: ±{round(accuracy)}m")
                
                    logger.info(f"📍 Procesando coordenadas: lat={lat:.6f}, lon={lon:.6f}")
                
                    # Obtener clima para las coordenadas
                    respuesta = chatbot.obtener_clima_por_coordenadas(lat, lon)
                    return jsonify({'respuesta': respuesta})
                
                except ValueError as e:
                    logger.error(f"❌ Error en formato de coordenadas: {str(e)}")
                    return jsonify({
                        'respuesta': 'Formato de coordenadas inválido. Por favor, inténtalo de nuevo.'
                    }), 400
                except WeatherAPIError as e:
                    logger.error(f"❌ Error al obtener clima: {str(e)}")
                    return jsonify({
                        'respuesta': f'Error al obtener el clima: {str(e)}'
                    }), 500
                except Exception as e:
                    logger.error(f"❌ Error procesando coordenadas: {str(e)}")
                    return jsonify({
                        'respuesta': 'Error al procesar tu ubicación. Por favor, inténtalo de nuevo.'
                    }), 500
            
            # Procesar mensaje normal
            logger.info("🔄 Procesando mensaje normal")
            try:
                respuesta = chatbot.procesar_mensaje(mensaje)

                # Si la respuesta es un dict con error, devolver error
                if isinstance(respuesta, dict) and 'error' in respuesta:
                    logger.info(f"❌Respuesta de error: {respuesta['error']}")
                    return jsonify({'respuesta': respuesta['error']}), 400

                # Si es dict con datos de clima/hora, devolver tal cual
                if isinstance(respuesta, dict):
                    logger.info(f"✅ Respuesta generada (objeto): {json.dumps(respuesta, ensure_ascii=False)}")
                    return jsonify({'respuesta': respuesta})

                # Si es string, devolver como texto
                logger.info(f"✅ Respuesta generada (texto): {str(respuesta)[:200]}...")
                return jsonify({'respuesta': respuesta})

            except Exception as e:
                logger.error(f"❌Error al procesar el mensaje: {str(e)}", exc_info=True)
                return jsonify({
                    'respuesta': '❌Ocurrió un error al procesar tu mensaje. Por favor, inténtalo de nuevo.'
                }), 500

        except Exception as e:
            logger.error(f"❌ERROR NO MANEJADO en la ruta /chat: {str(e)}", exc_info=True)
            return jsonify({
                'respuesta': '❌Lo siento, ha ocurrido un error en el servidor. Por favor, inténtalo de nuevo más tarde.'
            }), 500
        finally:
            logger.info("✅Solicitud finalizada\n" + "="*80 + "\n")
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Maneja errores 404 - Página no encontrada."""
        return jsonify({'error': 'Recurso no encontrado'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Maneja errores 500 - Error interno del servidor."""
        logger.error(f"Error interno del servidor: {error}")
        return jsonify({'error': 'Error interno del servidor'}), 500
    
    return app

# Crear y configurar la aplicación
app = create_app()

# Endpoint de prueba para verificar el despliegue
@app.route('/test')
def test():
    return jsonify({
        'status': 'ok',
        'message': 'La API está funcionando correctamente',
        'version': '1.0.0',
        'endpoints': {
            'chat': '/chat (POST)',
            'test': '/test (GET)',
            'status': '/ (GET)'
        }
    }), 200

if __name__ == '__main__':
    # Iniciar la aplicación
    app.run(debug=True, port=5000, host='0.0.0.0')