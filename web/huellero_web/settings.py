"""
Django settings for huellero_web project.
Corporación Hacia un Valle Solidario

Configurado para desarrollo local y producción (Railway)
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Directorio raíz del proyecto huellero_processor
PROJECT_ROOT = BASE_DIR.parent

# ===========================================
# CONFIGURACIÓN DE ENTORNO
# ===========================================

# Detectar entorno
DJANGO_ENV = os.environ.get('DJANGO_ENV', 'development')
IS_PRODUCTION = DJANGO_ENV == 'production'

# ===========================================
# SEGURIDAD
# ===========================================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-chvs-huellero-processor-key-change-in-production'
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

# Hosts permitidos
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# En producción, agregar el dominio de Railway
if IS_PRODUCTION:
    ALLOWED_HOSTS.extend(['.railway.app', '.up.railway.app'])

# CSRF trusted origins (necesario para Railway)
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
if IS_PRODUCTION:
    # Agregar dominios de Railway
    railway_url = os.environ.get('RAILWAY_PUBLIC_DOMAIN', '')
    if railway_url:
        CSRF_TRUSTED_ORIGINS.append(f'https://{railway_url}')
    CSRF_TRUSTED_ORIGINS.extend([
        'https://*.railway.app',
        'https://*.up.railway.app',
    ])
# Filtrar valores vacíos
CSRF_TRUSTED_ORIGINS = [x for x in CSRF_TRUSTED_ORIGINS if x]

# ===========================================
# APLICACIONES
# ===========================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Apps propias
    'apps.users',
    'apps.logistica',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Para servir archivos estáticos
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'huellero_web.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.static',
            ],
        },
    },
]

WSGI_APPLICATION = 'huellero_web.wsgi.application'

# ===========================================
# BASE DE DATOS
# ===========================================

# Por defecto usar SQLite para desarrollo
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# En producción o si hay DATABASE_URL, usar PostgreSQL
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    import dj_database_url
    DATABASES['default'] = dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
        conn_health_checks=True,
    )

# ===========================================
# VALIDACIÓN DE CONTRASEÑAS
# ===========================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
]

# ===========================================
# INTERNACIONALIZACIÓN
# ===========================================

LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

# ===========================================
# ARCHIVOS ESTÁTICOS
# ===========================================

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise para servir archivos estáticos en producción
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ===========================================
# CONFIGURACIÓN ADICIONAL
# ===========================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Autenticación
LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/users/redirect/'
LOGOUT_REDIRECT_URL = '/users/login/'

# ===========================================
# CONFIGURACIÓN DEL PROCESADOR DE HUELLERO
# ===========================================

try:
    from apps.logistica.pipeline import config
    DATA_INPUT_DIR = config.DIR_INPUT
    DATA_OUTPUT_DIR = config.DIR_OUTPUT
    DATA_MAESTRO_DIR = config.DIR_MAESTRO
    LOGS_DIR = config.DIR_LOGS
except ImportError:
    # Fallback si no se puede importar config
    DATA_INPUT_DIR = PROJECT_ROOT / 'data' / 'input'
    DATA_OUTPUT_DIR = PROJECT_ROOT / 'data' / 'output'
    DATA_MAESTRO_DIR = PROJECT_ROOT / 'data' / 'maestro'
    LOGS_DIR = PROJECT_ROOT / 'logs'

# ===========================================
# ÁREAS DISPONIBLES
# ===========================================

AREAS_CONFIG = {
    'logistica': {
        'nombre': 'Logística',
        'descripcion': 'Procesamiento de huellero del área de Logística',
        'icono': '📦',
        'color': '#2563eb',
    },
    # Futuras áreas:
    # 'supervision': {
    #     'nombre': 'Supervisión',
    #     'descripcion': 'Procesamiento de huellero del área de Supervisión',
    #     'icono': '👁️',
    #     'color': '#7c3aed',
    # },
}

# ===========================================
# CONFIGURACIÓN DE SEGURIDAD PARA PRODUCCIÓN
# ===========================================

if IS_PRODUCTION:
    # HTTPS
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # Seguridad adicional
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
