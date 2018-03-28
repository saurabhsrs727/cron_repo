"""
Django settings for myplex_cron_jobs project.

Generated by 'django-admin startproject' using Django 1.11.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import os
import json
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '(51%gqtrewdzro8(esv8&a9s5^ph@0abiv#bjhs^d&02ms&0y6'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# import settings from JSON config
PROJECT_SETTINGS_FILE = os.path.join(BASE_DIR, "conf", "pre_production_server.json")
CUSTOM_SETTINGS_FILE = os.path.join("/etc/myplex/myplex_service", "myplex_cron_service.json")
if os.path.exists(CUSTOM_SETTINGS_FILE):
    JSON_SETTINGS_FILE = CUSTOM_SETTINGS_FILE
else:
    JSON_SETTINGS_FILE = PROJECT_SETTINGS_FILE
JSON_SETTINGS = json.loads(open(JSON_SETTINGS_FILE).read())

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cron_apps.myplex_user',
    'cron_apps.paytm',
    'django_cron',
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

ROOT_URLCONF = 'myplex_cron_jobs.urls'

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

WSGI_APPLICATION = 'myplex_cron_jobs.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = JSON_SETTINGS['DATABASES']


# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'

# PAYTM SETTINGS
PAYTM_SETTINGS = JSON_SETTINGS['PAYTM_SETTINGS']

# CRON CLASSES
CRON_CLASSES = [
    "cron_apps.paytm.crons.PaytmRefundCron",

]
# Import Local settings
try:
    from myplex_cron_jobs.local_settings import *
except Exception:
    pass