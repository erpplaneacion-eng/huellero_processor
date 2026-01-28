"""
Django settings for huellero_web project.
Corporación Hacia un Valle Solidario
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Directorio raíz del proyecto huellero_processor
PROJECT_ROOT = BASE_DIR.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-chvs-huellero-processor-key-change-in-production'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Application definition
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

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ========== AUTENTICACIÓN ==========

LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/users/redirect/'
LOGOUT_REDIRECT_URL = '/users/login/'

# ========== CONFIGURACIÓN DEL PROCESADOR ==========

# Importar configuración del procesador para usar las mismas rutas
import sys
sys.path.insert(0, str(PROJECT_ROOT))
import config

# Directorios de datos (usando las rutas de config.py)
DATA_INPUT_DIR = config.DIR_INPUT
DATA_OUTPUT_DIR = config.DIR_OUTPUT
DATA_MAESTRO_DIR = config.DIR_MAESTRO
LOGS_DIR = config.DIR_LOGS

# ========== ÁREAS DISPONIBLES ==========

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
