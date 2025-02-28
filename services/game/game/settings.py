"""
Django settings for game project.

Generated by 'django-admin startproject' using Django 4.1.13.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

from pathlib import Path
import os
import math

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'daphne',
    'rest_framework',
    'channels',
    'game_app',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
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

ROOT_URLCONF = 'game.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'game.wsgi.application'
ASGI_APPLICATION = 'game.asgi.application'

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("redis", 6379)],
            "capacity": 1500,
            "expiry": 2,
        },
    },
}


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Celery settings

# Celery broker settings - connect to RabbitMQ running in the 'message-broker' container
CELERY_BROKER_URL = 'amqp://guest:guest@message-broker:5672//'
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# If using a result backend, such as Redis or PostgreSQL:
CELERY_RESULT_BACKEND = None  # You can change this if you need task results
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# If you need to set a timeout to handle long-running tasks gracefully
CELERY_TASK_TIME_LIMIT = 300  # Limit each task to a maximum of 5 minutes

CELERY_TASK_ROUTES = {
    'game_app.tasks.create_game': {
        'queue': 'game_tasks',
    },
    'game_app.tasks.launch_game': {
        'queue': 'game_tasks',
    },
}


# PONG GAME SETTINGS

FPS = 60
FIELD_HEIGHT = 1
FIELD_WIDTH = 1.5 * FIELD_HEIGHT
BALL_RADIUS = FIELD_WIDTH / 50
PADDLE_HEIGHT = FIELD_HEIGHT / 4
PADDLE_EDGE_ANGLE = 45
PADDLE_EDGE_ANGLE_RADIANS = math.radians(PADDLE_EDGE_ANGLE)
PADDLE_RADIUS = (PADDLE_HEIGHT / 2) / math.sin(PADDLE_EDGE_ANGLE_RADIANS)
PADDLE_OFFSET = (PADDLE_HEIGHT / 2) / math.tan(PADDLE_EDGE_ANGLE_RADIANS)
PADDLE_MOVE_AMOUNT = FIELD_HEIGHT / 50
INITIAL_BALL_SPEED = FIELD_HEIGHT / 2 / FPS
BALL_SPEED_INCREMENT = 1.1
MINIMUM_X_SPEED = FIELD_HEIGHT / 2 / FPS
WINNER_SCORE = 5
START_COUNTDOWN = 3
AI_REFRESH_RATE = 1

INITIAL_GAME_STATE = {
    "ball": {
        "x": FIELD_WIDTH / 2,
        "y": FIELD_HEIGHT / 2,
        "dx": INITIAL_BALL_SPEED,
        "dy": INITIAL_BALL_SPEED,
    },
    "scores": {"left": 0, "right": 0},
    "left_paddle_y": FIELD_HEIGHT / 2,
    "right_paddle_y": FIELD_HEIGHT / 2,
}


# RPS GAME SETTINGS

RPS_GAME_TIMER_LENGTH = 10
RPS_CHOICES = ["rock", "paper", "scissors"]


